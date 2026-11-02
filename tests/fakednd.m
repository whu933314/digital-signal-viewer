// GUI 測試用（tests_gui_mac.py s28）：在測試行程裡模擬「從 Finder 拖檔案放進 Tk 視窗」，走 tkdnd 原生的 DNDView
// （draggingEntered／draggingUpdated／prepare／performDragOperation）。不碰真的滑鼠、不搶焦點：
// 放下的位置＝暫時把 +[NSEvent mouseLocation] 換成指定座標（tkdnd 用它找游標下的元件），做完換回來；
// 排進主執行緒佇列，讓 Tk 的 update() 在事件迴圈裡執行（Python 回呼才在正確的 Tcl／GIL 狀態下被呼叫）。
// 編譯（測試自己會做）：clang -fobjc-arc -dynamiclib -framework AppKit -o libfakednd.dylib fakednd.m
#import <AppKit/AppKit.h>
#import <objc/runtime.h>

static NSPoint g_mouse;
static NSPoint fake_mouseLocation(id self, SEL _cmd) { return g_mouse; }

@interface DSVFakeDragInfo : NSObject
@property (strong) NSPasteboard *pb;
@end
@implementation DSVFakeDragInfo
- (NSPasteboard *)draggingPasteboard { return self.pb; }
- (NSDragOperation)draggingSourceOperationMask { return NSDragOperationEvery; }
- (id)draggingSource { return nil; }
- (NSPoint)draggingLocation { return NSZeroPoint; }
- (NSInteger)draggingSequenceNumber { return 1; }
- (NSWindow *)draggingDestinationWindow { return nil; }
@end

static volatile int g_state = 0;          // 0＝沒排；1＝排了還沒跑；2＝跑完
static long g_ops[5];
static char g_err[256];

int dsv_fake_drop_state(long *ops, char *err, int errlen) {
    for (int i = 0; i < 5; i++) ops[i] = g_ops[i];
    strncpy(err, g_err, errlen - 1); err[errlen - 1] = 0;
    return g_state;
}

// rootX/rootY：Tk 的螢幕座標（左上原點，和 winfo rootx 一樣）。paths：UTF-8，n 個。
// leave：0＝放下；1＝拖過去再離開（不放）；2＝只拖過去停著（不離開、不放：測試拖曳中的提示）。
int dsv_fake_drop(double rootX, double rootY, const char **paths, int n, int leave) {
    NSMutableArray *ps = [NSMutableArray array];
    for (int i = 0; i < n; i++) [ps addObject:[NSString stringWithUTF8String:paths[i]]];
    g_state = 1; g_err[0] = 0;
    for (int i = 0; i < 5; i++) g_ops[i] = -99;
    dispatch_async(dispatch_get_main_queue(), ^{
        @try {
            double H0 = [[[NSScreen screens] objectAtIndex:0] frame].size.height;
            NSPoint sp = NSMakePoint(rootX, H0 - rootY);
            NSView *dnd = nil;
            for (NSWindow *w in [NSApp windows]) {
                if (!NSPointInRect(sp, [w frame])) continue;
                for (NSView *v in [[w contentView] subviews])
                    if ([NSStringFromClass([v class]) isEqualToString:@"DNDView"]) { dnd = v; break; }
                if (dnd) break;
            }
            if (!dnd) { snprintf(g_err, sizeof g_err, "no DNDView window at %.0f,%.0f", rootX, rootY); g_state = 2; return; }
            NSPasteboard *pb = [NSPasteboard pasteboardWithUniqueName];
            [pb clearContents];
            NSMutableArray *urls = [NSMutableArray array];
            for (NSString *p in ps) [urls addObject:[NSURL fileURLWithPath:p]];
            [pb writeObjects:urls];
            DSVFakeDragInfo *fi = [DSVFakeDragInfo new]; fi.pb = pb; id info = fi;
            Method m = class_getClassMethod([NSEvent class], @selector(mouseLocation));
            IMP orig = method_setImplementation(m, (IMP)fake_mouseLocation);
            g_mouse = sp;
            g_ops[0] = (long)[(id<NSDraggingDestination>)dnd draggingEntered:info];
            g_ops[1] = (long)[(id<NSDraggingDestination>)dnd draggingUpdated:info];
            if (leave == 1) {
                [(id<NSDraggingDestination>)dnd draggingExited:info];
            } else if (leave == 2) {
                /* 只停在上面 */
            } else {
                g_ops[2] = (long)[(id<NSDraggingDestination>)dnd prepareForDragOperation:info];
                g_ops[3] = (long)[(id<NSDraggingDestination>)dnd performDragOperation:info];
            }
            method_setImplementation(m, orig);
            [pb releaseGlobally];
        } @catch (NSException *e) {
            snprintf(g_err, sizeof g_err, "exception %s", [[e description] UTF8String]);
        }
        g_state = 2;
    });
    return 0;
}

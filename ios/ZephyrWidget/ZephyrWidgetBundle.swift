import SwiftUI
import WidgetKit

@main
struct ZephyrWidgetBundle: WidgetBundle {
    var body: some Widget {
        #if os(iOS)
        ZephyrLiveActivity()
        ZephyrCircularWidget()
        ZephyrPM25CircularWidget()
        ZephyrInlineWidget()
        ZephyrRectangularWidget()
        ZephyrTempHumWidget()
        ZephyrTempPMWidget()
        ZephyrTempWindWidget()
        #endif
        ZephyrDesktopSmallWidget()
        ZephyrDesktopMediumWidget()
    }
}

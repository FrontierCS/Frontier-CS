#include <iostream>
#include <algorithm>
#include <vector>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    if (b == 1) {
        // Need 1 black component and w white components.
        // Construction:
        // Row 1: w white islands separated by black tiles. (.@.@.@...)
        // Row 2: All black tiles (@@@@@@...)
        // This ensures all black tiles are connected (via Row 2), and white tiles are isolated.
        
        int width = 2 * w - 1;
        cout << 2 << " " << width << "\n";
        
        // Row 1
        for (int i = 0; i < width; ++i) {
            if (i % 2 == 0) cout << '.';
            else cout << '@';
        }
        cout << "\n";
        
        // Row 2
        for (int i = 0; i < width; ++i) {
            cout << '@';
        }
        cout << "\n";
    } else if (w == 1) {
        // Need b black components and 1 white component.
        // Construction symmetric to b=1 case.
        // Row 1: b black islands separated by white tiles. (@.@.@...)
        // Row 2: All white tiles (......)
        
        int width = 2 * b - 1;
        cout << 2 << " " << width << "\n";
        
        // Row 1
        for (int i = 0; i < width; ++i) {
            if (i % 2 == 0) cout << '@';
            else cout << '.';
        }
        cout << "\n";
        
        // Row 2
        for (int i = 0; i < width; ++i) {
            cout << '.';
        }
        cout << "\n";
    } else {
        // b > 1 and w > 1.
        // Construction: 4 Rows.
        // Row 1: w-1 white islands separated by black. (.@.@...). Background Black.
        // Row 2: All Black (Buffer to connect Row 1 black parts).
        // Row 3: All White (Buffer to connect Row 4 white parts).
        // Row 4: b-1 black islands separated by white. (@.@.@...). Background White.
        //
        // Black components: 1 (Main body R1+R2) + (b-1 islands in R4) = b.
        // White components: (w-1 islands in R1) + 1 (Main body R3+R4) = w.
        
        int req_w_width = 2 * (w - 1) - 1;
        int req_b_width = 2 * (b - 1) - 1;
        int width = max(req_w_width, req_b_width);
        
        cout << 4 << " " << width << "\n";
        
        // Row 1: w-1 white islands
        for (int i = 0; i < width; ++i) {
            if (i < req_w_width) {
                if (i % 2 == 0) cout << '.';
                else cout << '@';
            } else {
                cout << '@'; // Padding with background color
            }
        }
        cout << "\n";
        
        // Row 2: Black Buffer
        for (int i = 0; i < width; ++i) {
            cout << '@';
        }
        cout << "\n";
        
        // Row 3: White Buffer
        for (int i = 0; i < width; ++i) {
            cout << '.';
        }
        cout << "\n";
        
        // Row 4: b-1 black islands
        for (int i = 0; i < width; ++i) {
            if (i < req_b_width) {
                if (i % 2 == 0) cout << '@';
                else cout << '.';
            } else {
                cout << '.'; // Padding with background color
            }
        }
        cout << "\n";
    }

    return 0;
}
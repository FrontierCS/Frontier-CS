#include <iostream>
#include <vector>
#include <string>
#include <cmath>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    // Optimization for balanced or nearly balanced counts
    // We can use a 1D strip of alternating colors.
    // This uses exactly b black tiles and w white tiles, which is optimal.
    if (abs(b - w) <= 1) {
        int h = b + w;
        cout << h << " " << 1 << "\n";
        char current;
        if (b > w) current = '@';
        else if (w > b) current = '.';
        else current = '@'; 

        for (int i = 0; i < h; ++i) {
            cout << current << "\n";
            current = (current == '@' ? '.' : '@');
        }
    } else {
        // General solution using width 2 strip
        // We construct a grid with two main regions: Top (Black) and Bottom (White).
        // The Top region contains w-1 isolated white dots.
        // The Bottom region contains b-1 isolated black dots.
        vector<string> grid;

        // Top Part: Black background
        if (w == 1) {
            // No extra white dots needed, just the main black component body
            grid.push_back("@@");
        } else {
            // Add blocks for white dots
            for (int i = 0; i < w - 1; ++i) {
                grid.push_back("@.");
                grid.push_back("@@");
            }
        }

        // Buffer layer to ensure separation between Main Black and isolated Black dots below
        // This layer belongs to the White background region
        grid.push_back("..");

        // Bottom Part: White background
        if (b > 1) {
            // Add blocks for black dots
            for (int i = 0; i < b - 1; ++i) {
                grid.push_back(".@");
                grid.push_back("..");
            }
        }
        // If b == 1, the buffer ".." serves as the Main White component.

        cout << grid.size() << " " << 2 << "\n";
        for (const auto& row : grid) {
            cout << row << "\n";
        }
    }

    return 0;
}
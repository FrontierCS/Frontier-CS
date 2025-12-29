#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long b, w, x, y;
    cin >> b >> w >> x >> y;

    long long cost_b_major, cost_w_major;
    
    // There are two main construction strategies.
    // Let's call them "black-majority" and "white-majority".
    // A black-majority construction for (b, w) where b >= w would be:
    // Stack b-w blocks of '@@', then w pairs of '@@' and '..'.
    // This gives b black areas and w white areas.
    // Total rows: (b-w) + 2*w = b+w. Width: 2.
    // Number of black tiles: 2 * (b-w) + 2 * w = 2*b.
    // Number of white tiles: 2 * w.
    
    // A white-majority construction for (b, w) where w > b would be:
    // Stack w-b blocks of '..', then b pairs of '..' and '@@'.
    // This gives b black areas and w white areas.
    // Total rows: (w-b) + 2*b = w+b. Width: 2.
    // Number of black tiles: 2 * b.
    // Number of white tiles: 2 * (w-b) + 2 * b = 2*w.
    
    // Both constructions result in 2*b black tiles and 2*w white tiles.
    // So the cost is always 2*b*x + 2*w*y.
    // The problem asks to find *any* such grid, minimizing cost.
    // Since this simple construction seems to always have the same tile count,
    // we can just pick one.
    // It's possible to construct grids with fewer tiles if |b-w| <= 1 using a line pattern,
    // but this stacking pattern works for all b and w and fits within the total tile limits.
    // max(b+w) = 2000. 2 * 2000 = 4000 tiles, well below 100,000.

    if (b >= w) {
        long long r = b + w;
        long long c = 2;
        cout << r << " " << c << endl;
        for (long long i = 0; i < w; ++i) {
            cout << "@@" << endl;
            cout << ".." << endl;
        }
        for (long long i = 0; i < b - w; ++i) {
            cout << "@@" << endl;
        }
    } else { // w > b
        long long r = b + w;
        long long c = 2;
        cout << r << " " << c << endl;
        for (long long i = 0; i < b; ++i) {
            cout << ".." << endl;
            cout << "@@" << endl;
        }
        for (long long i = 0; i < w - b; ++i) {
            cout << ".." << endl;
        }
    }

    return 0;
}
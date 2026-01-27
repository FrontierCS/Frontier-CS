#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    const int TOTAL = 2 * N;
    const int LIM = 100000;
    long long x, y;
    int minx = LIM, miny = LIM, maxx = 0, maxy = 0;
    for (int i = 0; i < TOTAL; ++i) {
        cin >> x >> y;
        minx = min(minx, (int)x);
        miny = min(miny, (int)y);
        maxx = max(maxx, (int)x);
        maxy = max(maxy, (int)y);
    }
    // Expand to ensure positive width and height and stay within bounds
    if (minx > 0) minx -= 1;
    if (maxx < LIM) maxx += 1;
    if (miny > 0) miny -= 1;
    if (maxy < LIM) maxy += 1;
    if (minx == maxx) {
        if (maxx < LIM) maxx++;
        else if (minx > 0) minx--;
    }
    if (miny == maxy) {
        if (maxy < LIM) maxy++;
        else if (miny > 0) miny--;
    }

    cout << 4 << "\n";
    cout << minx << " " << miny << "\n";
    cout << maxx << " " << miny << "\n";
    cout << maxx << " " << maxy << "\n";
    cout << minx << " " << maxy << "\n";
    return 0;
}
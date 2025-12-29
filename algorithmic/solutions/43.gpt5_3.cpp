#include <bits/stdc++.h>
using namespace std;

int main() {
    int N = 50, M = 50;
    vector<string> g(N, string(M, '#'));

    // Build a 3-wide serpentine corridor with 1-row separators between bands
    int bands = (N - 2) / 4; // Each band uses 3 rows + 1 separator; borders at 0 and N-1
    for (int b = 0; b < bands; ++b) {
        int rStart = 1 + b * 4; // rows rStart..rStart+2 are corridor
        // Open horizontal corridor for this band
        for (int r = rStart; r <= rStart + 2; ++r) {
            for (int c = 1; c <= M - 2; ++c) {
                g[r][c] = '.';
            }
        }
        // Open the vertical connector through the separator row at one end
        if (b < bands - 1) {
            int sep = rStart + 3;
            if (b % 2 == 0) {
                // connect on the right side (within columns 1..M-2)
                for (int c = M - 4; c <= M - 2; ++c) g[sep][c] = '.';
            } else {
                // connect on the left side
                for (int c = 1; c <= 3; ++c) g[sep][c] = '.';
            }
        }
    }

    // Place the 2x2 box near the start of the first band
    int rB = 1, cB = 3; // top-left of 2x2 box
    for (int dr = 0; dr < 2; ++dr)
        for (int dc = 0; dc < 2; ++dc)
            g[rB + dr][cB + dc] = 'B';

    // Place the 2x2 storage at the far end (last band, left side)
    int lastBandRow = 1 + (bands - 1) * 4; // top row of last band
    int rS = lastBandRow, cS = 1; // top-left of 2x2 storage
    for (int dr = 0; dr < 2; ++dr)
        for (int dc = 0; dc < 2; ++dc)
            g[rS + dr][cS + dc] = 'S';

    // Place the player near the far end, away from the box
    int rP = lastBandRow + 1; // middle row of last band corridor
    int cP = M - 3;           // near the right end inside the corridor
    g[rP][cP] = 'P';

    // Output
    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) cout << g[i] << "\n";
    return 0;
}
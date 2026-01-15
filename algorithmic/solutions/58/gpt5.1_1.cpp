#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long x;
    if (!(cin >> x)) return 0;

    const int MAX_BITS = 60;
    const int N = 260;
    const int cs = 70; // column for S (sum)

    vector<vector<int>> a(N + 1, vector<int>(N + 1, 0));

    int cp = 1;      // column for P (power of two)
    int row = 1;     // current last used row

    // Initialize first row
    a[1][1] = 1;     // start cell
    a[1][cs] = 1;    // S starts as 0 (no path reaches it)

    // Process bits 0..59
    for (int i = 0; i < MAX_BITS; ++i) {
        int bit = ( (x >> i) & 1LL );

        // Addition row: row -> row+1
        int r1 = row + 1;
        for (int j = 1; j <= N; ++j) {
            if (j < cp) {
                a[r1][j] = 0;
            } else if (j == cp) {
                a[r1][j] = 1; // propagate P
            } else if (j < cs) {
                a[r1][j] = bit ? 1 : 0; // carry P horizontally if bit==1
            } else if (j == cs) {
                a[r1][j] = 1; // update S
            } else {
                a[r1][j] = 0;
            }
        }
        row = r1;

        if (bit == 0) {
            // Doubling for bit=0: uses two rows then reset row
            int r2 = row + 1;
            for (int j = 1; j <= N; ++j) {
                if (j < cp) a[r2][j] = 0;
                else if (j == cp) a[r2][j] = 1;      // P down
                else if (j == cp + 1) a[r2][j] = 1;  // first copy towards new P
                else if (j < cs) a[r2][j] = 0;
                else if (j == cs) a[r2][j] = 1;      // S down
                else a[r2][j] = 0;
            }

            int r3 = r2 + 1;
            for (int j = 1; j <= N; ++j) {
                if (j < cp) a[r3][j] = 0;
                else if (j == cp) a[r3][j] = 1;      // P down
                else if (j == cp + 1) a[r3][j] = 1;  // P + P = 2P
                else if (j < cs) a[r3][j] = 0;
                else if (j == cs) a[r3][j] = 1;      // S down
                else a[r3][j] = 0;
            }

            int r4 = r3 + 1; // reset row: keep only new P at cp+1 and S at cs
            for (int j = 1; j <= N; ++j) {
                if (j < cp + 1) a[r4][j] = 0;
                else if (j == cp + 1) a[r4][j] = 1;  // new P
                else if (j < cs) a[r4][j] = 0;
                else if (j == cs) a[r4][j] = 1;      // S
                else a[r4][j] = 0;
            }

            row = r4;
            cp++;

        } else {
            // Doubling for bit=1: one row then reset row
            int r2 = row + 1;
            for (int j = 1; j <= N; ++j) {
                if (j < cp) a[r2][j] = 0;
                else if (j == cp) a[r2][j] = 1;      // P down
                else if (j == cp + 1) a[r2][j] = 1;  // P + P = 2P
                else if (j < cs) a[r2][j] = 0;
                else if (j == cs) a[r2][j] = 1;      // S down
                else a[r2][j] = 0;
            }

            int r3 = r2 + 1; // reset row
            for (int j = 1; j <= N; ++j) {
                if (j < cp + 1) a[r3][j] = 0;
                else if (j == cp + 1) a[r3][j] = 1;  // new P
                else if (j < cs) a[r3][j] = 0;
                else if (j == cs) a[r3][j] = 1;      // S
                else a[r3][j] = 0;
            }

            row = r3;
            cp++;
        }
    }

    // Finalization: kill P, keep S and route S to (N,N)

    int rKill = row + 1;
    if (rKill > N) rKill = N; // safety, though should not happen

    // Row to kill P and keep S
    for (int j = 1; j <= N; ++j) {
        if (j < cp) a[rKill][j] = 0;
        else if (j == cp) a[rKill][j] = 0;      // kill P
        else if (j < cs) a[rKill][j] = 0;
        else if (j == cs) a[rKill][j] = 1;      // S down
        else a[rKill][j] = 0;
    }

    int cur = rKill;

    // Vertical S-wire down to row N-1
    for (int i = cur + 1; i <= N - 1; ++i) {
        for (int j = 1; j <= N; ++j) {
            if (j == cs) a[i][j] = 1;   // S continues
            else a[i][j] = 0;
        }
    }

    // Last row: extend horizontally from cs to N
    for (int j = 1; j <= N; ++j) {
        if (j < cs) a[N][j] = 0;
        else a[N][j] = 1; // from cs to N, including S and final sink
    }

    // Output
    cout << N << '\n';
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            cout << a[i][j];
            if (j < N) cout << ' ';
        }
        if (i < N) cout << '\n';
    }

    return 0;
}
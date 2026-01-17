#include <bits/stdc++.h>
using namespace std;

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;

// Check if sequence a contains b as subsequence
bool isSubsequence(const vector<int>& a, const vector<int>& b) {
    int i = 0, j = 0;
    while (i < (int)a.size() && j < (int)b.size()) {
        if (a[i] == b[j]) j++;
        i++;
    }
    return j == (int)b.size();
}

// Construct path for a given order of rows p.
// Returns empty vector if construction fails (e.g., needed free column missing).
vector<pair<int,int>> constructPath(const vector<int>& p) {
    // Compute directions d[i] for each row in p
    int k = p.size(); // k should be n
    vector<int> d(k);
    d[0] = 0; // first row starts at left (Sx, L)

    // Check transitions and compute directions
    for (int i = 0; i < k-1; i++) {
        int cur = p[i], nxt = p[i+1];
        if (abs(cur - nxt) == 1) {
            // adjacent transition
            d[i+1] = 1 - d[i];
        } else {
            // jump transition
            if (d[i] == 0) {
                // need right free column (R+1)
                if (R+1 > m) return {};
                d[i+1] = 1;
            } else {
                // need left free column (L-1)
                if (L-1 < 1) return {};
                d[i+1] = 0;
            }
        }
    }

    vector<pair<int,int>> path;
    int x = Sx, y = L;
    path.push_back({x, y});

    // Complete first row
    if (d[0] == 0) {
        // left to right
        for (int col = L+1; col <= R; col++) {
            path.push_back({x, col});
        }
        y = R;
    } else {
        // right to left
        for (int col = R-1; col >= L; col--) {
            path.push_back({x, col});
        }
        y = L;
    }

    // Process each transition
    for (int i = 0; i < k-1; i++) {
        int cur_row = p[i];
        int nxt_row = p[i+1];
        if (abs(cur_row - nxt_row) == 1) {
            // adjacent move: vertical step to next row, same column
            path.push_back({nxt_row, y});
            x = nxt_row;
            // complete next row
            if (d[i+1] == 0) {
                // left to right
                for (int col = L+1; col <= R; col++) {
                    path.push_back({x, col});
                }
                y = R;
            } else {
                // right to left
                for (int col = R-1; col >= L; col--) {
                    path.push_back({x, col});
                }
                y = L;
            }
        } else {
            // jump move
            if (d[i] == 0) {
                // use right free column: current at (cur_row, R)
                // step to (cur_row, R+1)
                path.push_back({cur_row, R+1});
                // vertical move in column R+1
                if (nxt_row > cur_row) {
                    for (int r = cur_row+1; r <= nxt_row; r++) {
                        path.push_back({r, R+1});
                    }
                } else {
                    for (int r = cur_row-1; r >= nxt_row; r--) {
                        path.push_back({r, R+1});
                    }
                }
                // step to entry point (nxt_row, R)
                path.push_back({nxt_row, R});
                x = nxt_row;
                // complete next row right-to-left
                for (int col = R-1; col >= L; col--) {
                    path.push_back({x, col});
                }
                y = L;
            } else {
                // use left free column: current at (cur_row, L)
                // step to (cur_row, L-1)
                path.push_back({cur_row, L-1});
                // vertical move in column L-1
                if (nxt_row > cur_row) {
                    for (int r = cur_row+1; r <= nxt_row; r++) {
                        path.push_back({r, L-1});
                    }
                } else {
                    for (int r = cur_row-1; r >= nxt_row; r--) {
                        path.push_back({r, L-1});
                    }
                }
                // step to entry point (nxt_row, L)
                path.push_back({nxt_row, L});
                x = nxt_row;
                // complete next row left-to-right
                for (int col = L+1; col <= R; col++) {
                    path.push_back({x, col});
                }
                y = R;
            }
        }
    }
    return path;
}

// Generate order: increasing from Sx to n, then from 1 to Sx-1
vector<int> increasingOrder() {
    vector<int> p;
    for (int r = Sx; r <= n; r++) p.push_back(r);
    for (int r = 1; r < Sx; r++) p.push_back(r);
    return p;
}

// Generate order: decreasing from Sx to 1, then from n to Sx+1
vector<int> decreasingOrder() {
    vector<int> p;
    for (int r = Sx; r >= 1; r--) p.push_back(r);
    for (int r = n; r > Sx; r--) p.push_back(r);
    return p;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    q.resize(Lq);
    for (int i = 0; i < Lq; i++) cin >> q[i];

    // Check starting condition
    if (Sy != L) {
        // According to problem, Sy = L is guaranteed.
        cout << "NO\n";
        return 0;
    }

    // Case 1: No free columns (L=1 and R=m)
    if (L == 1 && R == m) {
        if (Sx != 1 && Sx != n) {
            cout << "NO\n";
            return 0;
        }
        vector<int> p;
        if (Sx == 1) {
            for (int i = 1; i <= n; i++) p.push_back(i);
        } else {
            for (int i = n; i >= 1; i--) p.push_back(i);
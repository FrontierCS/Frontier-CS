#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    while (true) {
        int n;
        if (!(cin >> n)) break;
        vector<string> rows(n);
        for (int i = 0; i < n; ++i) cin >> rows[i];
        vector<vector<int>> C(n, vector<int>(n));
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                C[i][j] = rows[i][j] - '0';

        // Heuristic greedy construction with two ends and at most one color switch
        // Try multiple seeds to increase chance; keep lexicographically best found
        vector<int> best;
        auto check = [&](const vector<int>& p)->bool{
            if ((int)p.size() != n) return false;
            int changes = 0;
            for (int i = 0; i + 2 <= n; ++i) {
                int a = C[p[i]-1][p[i+1]-1];
                int b = C[p[i+1]-1][p[i+2]-1 == n ? 0 : p[i+2]-1]; // dummy
                (void)b;
            }
            // compute c_i
            vector<int> c(n);
            for (int i = 0; i < n-1; ++i) c[i] = C[p[i]-1][p[i+1]-1];
            c[n-1] = C[p[n-1]-1][p[0]-1];
            int cnt = 0;
            for (int i = 0; i < n-1; ++i) if (c[i] != c[i+1]) ++cnt;
            return cnt <= 1;
        };

        auto attempt = [&](int start)->vector<int>{
            deque<int> dq;
            vector<char> used(n, 0);
            dq.push_back(start);
            used[start-1] = 1;
            bool switched = false;
            int colorLeft = -1, colorRight = -1; // desired colors for edges when extending
            while ((int)dq.size() < n) {
                int pick = -1, endSel = -1; // 0: left, 1: right
                // Try to keep lexicographically small: prefer smallest label placement at leftmost position if possible
                for (int v = 1; v <= n; ++v) if (!used[v-1]) {
                    // Try append to left keeping color if set
                    bool okL = false, okR = false;
                    int cl = C[v-1][dq.front()-1];
                    int cr = C[dq.back()-1][v-1];
                    if (colorLeft == -1 || cl == colorLeft) okL = true;
                    if (colorRight == -1 || cr == colorRight) okR = true;
                    if (okL || okR) {
                        pick = v;
                        endSel = okL ? 0 : 1;
                        break;
                    }
                }
                if (pick == -1) {
                    // need to allow a switch if not yet
                    if (switched) {
                        // force place anyway with minimal damage: pick smallest and place to left
                        for (int v = 1; v <= n; ++v) if (!used[v-1]) { pick = v; endSel = 0; break; }
                    } else {
                        // set switch by defining colors on one side
                        for (int v = 1; v <= n; ++v) if (!used[v-1]) {
                            int cl = C[v-1][dq.front()-1];
                            int cr = C[dq.back()-1][v-1];
                            // Try to set colorLeft or colorRight to accept this
                            if (colorLeft == -1) { colorLeft = cl; pick = v; endSel = 0; switched = true; break; }
                            if (colorRight == -1) { colorRight = cr; pick = v; endSel = 1; switched = true; break; }
                        }
                    }
                }
                if (pick == -1) {
                    // fallback
                    for (int v = 1; v <= n; ++v) if (!used[v-1]) { pick = v; endSel = 0; break; }
                }
                if (endSel == 0) {
                    if (colorLeft == -1) colorLeft = C[pick-1][dq.front()-1];
                    dq.push_front(pick);
                } else {
                    if (colorRight == -1) colorRight = C[dq.back()-1][pick-1];
                    dq.push_back(pick);
                }
                used[pick-1] = 1;
            }
            vector<int> p(dq.begin(), dq.end());
            if (check(p)) return p;
            return {};
        };

        // Try seeds in increasing order to aim for lexicographically small
        for (int s0 = 1; s0 <= n; ++s0) {
            auto p = attempt(s0);
            if (p.empty()) continue;
            if (best.empty() || p < best) best = p;
        }
        if (best.empty()) {
            cout << -1 << "\n";
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << best[i];
            }
            cout << "\n";
        }
    }
    return 0;
}
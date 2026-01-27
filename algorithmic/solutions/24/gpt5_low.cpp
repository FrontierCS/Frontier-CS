#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<string> S(n);
        for (int i = 0; i < n; ++i) {
            cin >> S[i];
            if ((int)S[i].size() < n) {
                // In case input has spaces (unlikely per sample), read remaining tokens
                string t;
                while ((int)S[i].size() < n && cin >> t) S[i] += t;
            }
        }
        auto edge = [&](int a, int b)->int{
            return S[a][b]-'0';
        };

        // Build permutation p as a cyclic order maintaining at most one change
        vector<int> p;
        p.push_back(0);
        p.push_back(1);
        // c[i] is color of edge between p[i] and p[(i+1)%k], size k
        auto rebuild_c = [&](const vector<int>& pp)->vector<int>{
            int k = (int)pp.size();
            vector<int> c(k);
            for (int i = 0; i < k; ++i) {
                int j = (i+1==k)?0:i+1;
                c[i] = edge(pp[i], pp[j]);
            }
            return c;
        };
        auto count_changes = [&](const vector<int>& c)->int{
            int k = (int)c.size();
            int cnt = 0;
            for (int i = 0; i+1 < k; ++i) if (c[i]!=c[i+1]) ++cnt;
            return cnt;
        };

        vector<int> c = rebuild_c(p);
        int changes = count_changes(c);

        auto test_insert_delta = [&](int pos, int v)->int{
            int k = (int)p.size();
            if (k==0) return 0; // not used
            int j = (pos-1 + k) % k;
            int prev = p[j];
            int next = p[pos % k];
            int a = edge(prev, v);
            int b = edge(v, next);

            int old_diff = 0;
            if (k >= 2) {
                if (j >= 1) {
                    if (c[j-1] != c[j]) ++old_diff;
                }
                if (j <= k-2) {
                    if (c[j] != c[j+1]) ++old_diff;
                }
            }
            int new_diff = 0;
            if (k >= 1) {
                if (j >= 1) {
                    if (c[j-1] != a) ++new_diff;
                }
                // compare at i=j (always valid in new length k+1)
                if (a != b) ++new_diff;
                if (j <= k-2) {
                    if (b != c[j+1]) ++new_diff;
                }
            }
            return changes - old_diff + new_diff;
        };

        auto do_insert = [&](int pos, int v){
            // insert v before p[pos]
            p.insert(p.begin()+pos, v);
            c = rebuild_c(p);
            changes = count_changes(c);
        };

        bool ok = true;
        for (int v = 2; v < n; ++v) {
            int k = (int)p.size();
            int bestPos = -1;
            for (int pos = 0; pos <= k; ++pos) {
                int new_changes = test_insert_delta(pos, v);
                if (new_changes <= 1) {
                    bestPos = pos;
                    break; // choose earliest position to bias lexicographic small
                }
            }
            if (bestPos == -1) {
                ok = false;
                break;
            }
            do_insert(bestPos, v);
        }
        if (!ok) {
            cout << -1 << "\n";
            continue;
        }

        // Among all rotations that are valid (≤1 change), choose lexicographically smallest
        int k = n;
        // Precompute all c for current p
        // Try each rotation r: rotated p_r[i] = p[(r+i)%n]
        auto valid_changes_for_rotation = [&](int r)->int{
            // Build c_rot[i] for i in [0..n-1]
            int cnt = 0;
            for (int i = 0; i+1 < n; ++i) {
                int a1 = p[(r + i) % n];
                int b1 = p[(r + i + 1) % n];
                int a2 = p[(r + i + 1) % n];
                int b2 = p[(r + i + 2) % n];
                int c1 = edge(a1, b1);
                int c2 = edge(a2, b2);
                if (c1 != c2) ++cnt;
                if (cnt > 1) return cnt; // early exit
            }
            return cnt;
        };

        int best_r = 0;
        for (int r = 0; r < n; ++r) {
            int ch = valid_changes_for_rotation(r);
            if (ch <= 1) {
                if (best_r == 0) {
                    best_r = r;
                } else {
                    // compare lexicographically rotated sequences
                    bool better = false;
                    for (int i = 0; i < n; ++i) {
                        int a = p[(r + i) % n];
                        int b = p[(best_r + i) % n];
                        if (a != b) {
                            if (a < b) better = true;
                            break;
                        }
                    }
                    if (better) best_r = r;
                }
            }
        }

        // Output rotation best_r (1-indexed)
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << (p[(best_r + i) % n] + 1);
        }
        cout << "\n";
    }
    return 0;
}
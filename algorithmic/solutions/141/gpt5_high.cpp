#include <bits/stdc++.h>
using namespace std;

static inline bool ask(int c) {
    cout << "? " << c << endl;
    cout.flush();
    string s;
    if (!(cin >> s)) exit(0);
    return (s[0] == 'Y' || s[0] == 'y');
}

static inline void reset_mem() {
    cout << "R" << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    if (!(cin >> n >> k)) return 0;

    if (n <= 0) {
        cout << "! 0" << endl;
        cout.flush();
        return 0;
    }

    // Special fallback for k == 1 (may be too many operations for large n)
    if (k == 1) {
        int distinct = 0;
        vector<int> reps;
        for (int i = 1; i <= n; ++i) {
            bool found = false;
            for (int rep : reps) {
                reset_mem();
                ask(rep);
                if (ask(i)) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                distinct++;
                reps.push_back(i);
            }
        }
        cout << "! " << distinct << endl;
        cout.flush();
        return 0;
    }

    int S = min(k / 2, n);
    if (S <= 0) S = 1;

    int B = (n + S - 1) / S;
    vector<vector<int>> blocks(B);
    for (int i = 0; i < n; ++i) {
        blocks[i / S].push_back(i + 1);
    }

    // Compute leaders (distinct within each block)
    vector<vector<int>> leaders(B);
    for (int b = 0; b < B; ++b) {
        reset_mem();
        for (int x : blocks[b]) {
            bool y = ask(x);
            if (!y) leaders[b].push_back(x);
        }
    }

    // Pairwise elimination: for each later block, remove those matching previous blocks
    int distinct = 0;
    for (int q = 0; q < B; ++q) {
        vector<char> matched(leaders[q].size(), 0);
        for (int p = 0; p < q; ++p) {
            if (leaders[p].empty()) continue;
            if (leaders[p].size() + leaders[q].size() > (size_t)k) continue; // safety
            reset_mem();
            for (int u : leaders[p]) ask(u);
            for (size_t idx = 0; idx < leaders[q].size(); ++idx) {
                if (matched[idx]) continue;
                if (ask(leaders[q][idx])) matched[idx] = 1;
            }
            // Early exit if all matched
            bool allMatched = true;
            for (auto m : matched) if (!m) { allMatched = false; break; }
            if (allMatched) break;
        }
        for (auto m : matched) if (!m) distinct++;
    }

    cout << "! " << distinct << endl;
    cout.flush();
    return 0;
}
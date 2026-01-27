#include <bits/stdc++.h>
using namespace std;

static inline int ask(const vector<int>& v) {
    cout << "?";
    for (int x : v) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int getMaxFromSet(const vector<int>& S, int n) {
    int s = (int)S.size();
    // Initial query with first n elements
    vector<int> processed;
    processed.reserve(s);
    vector<int> Q;
    Q.reserve(n);
    for (int i = 0; i < n; ++i) {
        Q.push_back(S[i]);
        processed.push_back(S[i]);
    }
    int cand = ask(Q);
    int idx = n;
    // Process remaining elements in blocks of size up to (n-1)
    while (idx < s) {
        int take = min(n - 1, s - idx);
        Q.clear();
        Q.push_back(cand);
        // Add new elements
        for (int t = 0; t < take; ++t) {
            Q.push_back(S[idx + t]);
        }
        // Fill remaining slots with already processed elements (excluding cand and duplicates)
        int need = n - 1 - take;
        for (int i = 0, added = 0; added < need && i < (int)processed.size(); ++i) {
            int x = processed[i];
            bool dup = (x == cand);
            if (!dup) {
                for (int j = 1; j < (int)Q.size(); ++j) {
                    if (Q[j] == x) { dup = true; break; }
                }
            }
            if (!dup) {
                Q.push_back(x);
                ++added;
            }
        }
        cand = ask(Q);
        // Mark newly processed
        for (int t = 0; t < take; ++t) {
            processed.push_back(S[idx + t]);
        }
        idx += take;
    }
    return cand;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int N = n * n;
        vector<int> remaining(N);
        iota(remaining.begin(), remaining.end(), 1);
        vector<int> answer;
        answer.reserve(N - n + 1);
        for (int k = 0; k < N - n + 1; ++k) {
            int s = (int)remaining.size();
            // Build a working array S to pass to getMaxFromSet
            // Ensure size >= n here
            vector<int> S = remaining;
            int mx = getMaxFromSet(S, n);
            answer.push_back(mx);
            // Remove mx from remaining
            auto it = find(remaining.begin(), remaining.end(), mx);
            if (it != remaining.end()) remaining.erase(it);
        }
        cout << "!";
        for (int x : answer) cout << " " << x;
        cout << endl;
        cout.flush();
    }
    return 0;
}
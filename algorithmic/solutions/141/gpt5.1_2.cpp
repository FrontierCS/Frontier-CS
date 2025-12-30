#include <bits/stdc++.h>
using namespace std;

char ask(int c) {
    cout << "? " << c << endl;
    char ch;
    if (!(cin >> ch)) exit(0);
    return ch;
}

void reset_mem() {
    cout << "R" << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    int d = 0;

    if (k == 1) {
        // Naive equality-based algorithm for k = 1
        vector<int> reps; // representatives of distinct types
        for (int i = 1; i <= n; ++i) {
            bool eq = false;
            for (int r : reps) {
                reset_mem();
                ask(r); // response ignored
                char ch2 = ask(i);
                if (ch2 == 'Y') {
                    eq = true;
                    break;
                }
            }
            if (!eq) reps.push_back(i);
        }
        d = (int)reps.size();
        cout << "! " << d << endl;
        return 0;
    }

    // k > 1: window-based algorithm
    int B = min(k / 2, n);
    if (B <= 0) B = 1;

    vector<vector<int>> windows;
    vector<int> window_of(n + 1);
    int m = 0;
    for (int i = 1; i <= n; i += B) {
        int r = min(n, i + B - 1);
        windows.emplace_back();
        for (int j = i; j <= r; ++j) {
            windows.back().push_back(j);
            window_of[j] = m;
        }
        ++m;
    }

    vector<vector<int>> L(m);          // local-first indices per window
    vector<char> is_first(n + 1, 0);   // local-first flag
    vector<char> is_new(n + 1, 0);     // candidate global-first flag

    // Preprocess each window to find local-first indices
    for (int t = 0; t < m; ++t) {
        reset_mem();
        for (int idx : windows[t]) {
            char ch = ask(idx);
            if (ch == 'N') {
                L[t].push_back(idx);
                is_first[idx] = 1;
                is_new[idx] = 1;
            }
        }
    }

    // Cross-check between windows
    for (int i = 0; i < m; ++i) {
        for (int j = i + 1; j < m; ++j) {
            // Check if there is any still-candidate in L[j]
            bool any_new = false;
            for (int idx : L[j]) {
                if (is_new[idx]) {
                    any_new = true;
                    break;
                }
            }
            if (!any_new) continue;

            reset_mem();
            // Load all local-firsts from window i
            for (int idx : L[i]) {
                ask(idx); // response ignored
            }
            // Test candidates from window j
            for (int idx : L[j]) {
                if (!is_new[idx]) continue;
                char ch = ask(idx);
                if (ch == 'Y') {
                    is_new[idx] = 0;
                }
            }
        }
    }

    // Count global-first indices
    d = 0;
    for (int i = 1; i <= n; ++i) {
        if (is_new[i]) ++d;
    }

    cout << "! " << d << endl;
    return 0;
}
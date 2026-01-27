#include <bits/stdc++.h>
using namespace std;

static inline int ask(int i, int j) {
    cout << "? " << i+1 << " " << j+1 << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, n-1);

    int s = dist(rng);

    vector<int> or_with_s(n, -1);
    int m = INT_MAX;
    bool any_even = false;
    for (int i = 0; i < n; ++i) if (i != s) {
        int x = ask(s, i);
        or_with_s[i] = x;
        m = min(m, x);
        if ((x & 1) == 0) any_even = true;
    }

    vector<int> C;
    for (int i = 0; i < n; ++i) if (i != s && or_with_s[i] == m) C.push_back(i);

    vector<int> ans(n, -1);

    // If s is zero, we can directly read all values from initial queries
    if (m == 1 && C.size() == 1 && any_even) {
        int z = s;
        ans[z] = 0;
        for (int i = 0; i < n; ++i) if (i != z) ans[i] = or_with_s[i];
        cout << "! ";
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << ans[i];
        }
        cout << endl;
        cout.flush();
        return 0;
    }

    int z = -1;
    if (m == 1 && C.size() == 1 && !any_even) {
        // s has value 1, the unique minimal corresponds to zero
        z = C[0];
    } else {
        // Shrink candidate set by choosing an element r in C and filtering
        vector<int> S = C;
        while ((int)S.size() > 1) {
            int r = S[uniform_int_distribution<int>(0, (int)S.size()-1)(rng)];
            int mn = INT_MAX;
            vector<int> vals(S.size(), -1);
            for (size_t idx = 0; idx < S.size(); ++idx) {
                int i = S[idx];
                if (i == r) continue; // skip invalid ask(i,i)
                int x = ask(i, r);
                vals[idx] = x;
                if (x < mn) mn = x;
            }
            vector<int> T;
            for (size_t idx = 0; idx < S.size(); ++idx) {
                int i = S[idx];
                if (i == r) continue;
                if (vals[idx] == mn) T.push_back(i);
            }
            // It's possible that r itself should be included if it belongs to minimizers,
            // but since there always exists i != r with p_i subset-of p_r (e.g., 0), T won't be empty.
            S.swap(T);
        }
        z = S[0];
    }

    // Now retrieve full permutation using z (p_z = 0)
    ans[z] = 0;
    for (int i = 0; i < n; ++i) if (i != z) {
        ans[i] = ask(z, i);
    }

    cout << "! ";
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<char> ans(n, '?');

    int s1_type = -1;  // 0 -> '(', 1 -> ')'
    int openIdx = -1;  // index (1-based) known to be '('
    int pFound = -1;   // position j where orientation determined

    vector<int> q1(n + 1, -1), q2(n + 1, -1);

    // Phase 1: determine orientation of s1 and locate an '(' (openIdx)
    for (int j = 2; j <= n; ++j) {
        if (s1_type != -1) break;

        // Query [1, j]
        cout << "0 2 " << 1 << " " << j << "\n";
        cout.flush();
        int v1;
        if (!(cin >> v1)) return 0;
        q1[j] = v1;

        if (v1 == 1) {
            // s1='(', sj=')'
            s1_type = 0;
            ans[0] = '(';
            ans[j - 1] = ')';
            openIdx = 1;
            pFound = j;
            break;
        } else {
            // Need second query [j, 1]
            cout << "0 2 " << j << " " << 1 << "\n";
            cout.flush();
            int v2;
            if (!(cin >> v2)) return 0;
            q2[j] = v2;

            if (v2 == 1) {
                // sj='(', s1=')'
                s1_type = 1;
                ans[0] = ')';
                ans[j - 1] = '(';
                openIdx = j;
                pFound = j;
                break;
            }
        }
    }

    // Orientation must be determined
    if (s1_type == -1) {
        // Should not happen due to problem guarantees, but guard anyway
        // Assume s1 is '(' and classify trivially (will likely be wrong if reached)
        s1_type = 0;
        ans[0] = '(';
        openIdx = 1;
        pFound = 1;
    }

    // Phase 2: classify indices <= pFound using stored queries
    if (s1_type == 0) {
        // s1 = '(' , openIdx = 1
        // For k < pFound: q1[k]==0, so sk='('
        for (int k = 2; k < pFound; ++k) {
            ans[k - 1] = '(';
        }
        // pFound already set: ans[pFound-1] = ')'
    } else {
        // s1 = ')' , openIdx = pFound
        // For k < pFound: q2[k]==0, so sk=')'
        for (int k = 2; k < pFound; ++k) {
            ans[k - 1] = ')';
        }
        // pFound already set: ans[pFound-1] = '('
    }

    // Phase 3: classify remaining indices > pFound
    if (openIdx == 1) {
        // We know s1='('
        for (int k = pFound + 1; k <= n; ++k) {
            cout << "0 2 " << 1 << " " << k << "\n";
            cout.flush();
            int v;
            if (!(cin >> v)) return 0;
            if (v == 1) ans[k - 1] = ')';
            else ans[k - 1] = '(';
        }
    } else {
        // We know openIdx has '('
        for (int k = pFound + 1; k <= n; ++k) {
            cout << "0 2 " << openIdx << " " << k << "\n";
            cout.flush();
            int v;
            if (!(cin >> v)) return 0;
            if (v == 1) ans[k - 1] = ')';
            else ans[k - 1] = '(';
        }
    }

    // Output final answer
    cout << "1 ";
    for (int i = 0; i < n; ++i) cout << ans[i];
    cout << "\n";
    cout.flush();

    return 0;
}
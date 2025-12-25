#include <bits/stdc++.h>
using namespace std;

const int M = 12;                // number of sets
const int N = 300;               // maximum value
const int LEN = 2 * N - 1;       // 599

vector<int> sets[M];             // each set is a list of indices (1‑based)

void precompute() {
    // generate 599 distinct 12‑bit numbers with exactly 6 ones
    vector<int> signatures;
    for (int mask = 0; mask < (1 << M); ++mask) {
        if (__builtin_popcount(mask) == 6) {
            signatures.push_back(mask);
            if (signatures.size() == LEN) break;
        }
    }

    // for each bit j, collect indices i where bit j is set in signatures[i-1]
    for (int j = 0; j < M; ++j) {
        sets[j].clear();
        for (int i = 1; i <= LEN; ++i) {
            if ((signatures[i - 1] >> j) & 1) {
                sets[j].push_back(i);
            }
        }
    }
}

void solve() {
    int t;
    cin >> t;
    precompute();

    while (t--) {
        int n;
        cin >> n;                // n is always 300, but we read it anyway
        if (n == -1) exit(0);    // previous answer was wrong

        int ans = -1;
        for (int x = 1; x <= n; ++x) {
            int cnt = 0;
            bool candidate = true;
            for (int j = 0; j < M; ++j) {
                // ask query for number x and set sets[j]
                cout << "? " << x << " " << sets[j].size();
                for (int idx : sets[j]) cout << " " << idx;
                cout << endl;
                cout.flush();

                int response;
                cin >> response;
                if (response == -1) exit(0);   // invalid query or wrong answer

                cnt += response;
                if (cnt > 6) {                 // cannot be the unique number
                    candidate = false;
                    break;
                }
            }
            if (candidate && cnt == 6) {
                ans = x;
                break;
            }
        }

        cout << "! " << ans << endl;
        cout.flush();
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    solve();
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

const int M = 12;          // number of bits
const int INDEX_COUNT = 599; // 2*300 - 1
const int MAX_N = 300;

vector<int> sets[M];
int mask[INDEX_COUNT + 1]; // mask for each index (1..INDEX_COUNT)

void precompute() {
    // generate all 12-bit masks with exactly 6 bits set
    vector<int> candidates;
    for (int msk = 0; msk < (1 << M); ++msk) {
        if (__builtin_popcount(msk) == 6) {
            candidates.push_back(msk);
        }
    }
    // take the first 599 distinct masks
    for (int i = 1; i <= INDEX_COUNT; ++i) {
        mask[i] = candidates[i - 1];
    }
    // build the sets S_b for each bit b (0-indexed)
    for (int b = 0; b < M; ++b) {
        sets[b].clear();
        for (int i = 1; i <= INDEX_COUNT; ++i) {
            if (mask[i] & (1 << b)) {
                sets[b].push_back(i);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    precompute();

    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        if (n == -1) {
            return 0; // previous answer was wrong
        }

        vector<int> cnt(MAX_N + 1, 0);
        for (int x = 1; x <= n; ++x) {
            for (int b = 0; b < M; ++b) {
                // ask query: is x in S_b?
                cout << "? " << x << " " << sets[b].size();
                for (int idx : sets[b]) {
                    cout << " " << idx;
                }
                cout << endl;
                cout.flush();

                int resp;
                cin >> resp;
                if (resp == -1) {
                    return 0; // invalid query or query limit exceeded
                }
                if (resp == 1) {
                    ++cnt[x];
                }
                // if we already know this number appears at least twice, stop asking for it
                if (cnt[x] > 6) {
                    break;
                }
            }
        }

        // find the number that got exactly 6 positive answers
        int ans = -1;
        for (int x = 1; x <= n; ++x) {
            if (cnt[x] == 6) {
                ans = x;
                break;
            }
        }

        cout << "! " << ans << endl;
        cout.flush();
    }

    return 0;
}
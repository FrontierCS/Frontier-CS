#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) {
        cin >> cost[i];
    }
    vector<bitset<401>> set_cover(m + 1);
    for (int i = 1; i <= n; ++i) {
        int k;
        cin >> k;
        for (int j = 0; j < k; ++j) {
            int a;
            cin >> a;
            set_cover[a][i] = 1;
        }
    }
    bitset<401> uncovered;
    for (int i = 1; i <= n; ++i) {
        uncovered[i] = 1;
    }
    vector<int> selected;
    while (uncovered.any()) {
        int best_j = -1;
        long long best_c = 0;
        int best_num = 0;
        for (int j = 1; j <= m; ++j) {
            bitset<401> temp = set_cover[j] & uncovered;
            int num = temp.count();
            if (num == 0) continue;
            long long c = cost[j];
            bool better = false;
            if (best_j == -1) {
                better = true;
            } else {
                long long left = c * (long long)best_num;
                long long right = best_c * (long long)num;
                if (left < right) {
                    better = true;
                } else if (left > right) {
                    better = false;
                } else {
                    if (num > best_num) {
                        better = true;
                    }
                }
            }
            if (better) {
                best_j = j;
                best_c = c;
                best_num = num;
            }
        }
        if (best_j == -1) {
            break;
        }
        selected.push_back(best_j);
        uncovered &= ~set_cover[best_j];
    }
    cout << selected.size() << '\n';
    sort(selected.begin(), selected.end());
    for (int x : selected) {
        cout << x << ' ';
    }
    cout << '\n';
}
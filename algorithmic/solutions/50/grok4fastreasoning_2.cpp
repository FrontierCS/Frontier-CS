#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; i++) {
        cin >> cost[i];
    }
    vector<vector<int>> elem_in_set(m + 1);
    for (int i = 1; i <= n; i++) {
        int k;
        cin >> k;
        for (int j = 0; j < k; j++) {
            int a;
            cin >> a;
            elem_in_set[a].push_back(i);
        }
    }
    vector<bool> is_covered(n + 1, false);
    int uncovered = n;
    vector<int> selected;
    vector<bool> used(m + 1, false);
    while (uncovered > 0) {
        long long best_num = -1;
        long long best_den = 1;
        int best_set = -1;
        for (int s = 1; s <= m; s++) {
            if (used[s]) continue;
            int new_count = 0;
            for (int e : elem_in_set[s]) {
                if (!is_covered[e]) new_count++;
            }
            if (new_count == 0) continue;
            long long c = cost[s];
            bool better = false;
            if (best_set == -1) {
                better = true;
            } else {
                // check if new_count / c > best_num / best_den
                // i.e. new_count * best_den > best_num * c
                if (new_count * best_den > best_num * c) {
                    better = true;
                }
            }
            if (better) {
                best_num = new_count;
                best_den = c;
                best_set = s;
            }
        }
        if (best_set == -1) {
            // cannot cover, but assume possible
            break;
        }
        used[best_set] = true;
        selected.push_back(best_set);
        for (int e : elem_in_set[best_set]) {
            if (!is_covered[e]) {
                is_covered[e] = true;
                uncovered--;
            }
        }
    }
    cout << selected.size() << endl;
    sort(selected.begin(), selected.end());
    for (int id : selected) {
        cout << id << " ";
    }
    cout << endl;
    return 0;
}
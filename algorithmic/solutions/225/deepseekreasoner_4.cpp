#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, q;
    scanf("%d %d", &n, &q);
    vector<int> a(n + 1);
    vector<int> pos_value(n + 1); // singleton set ID for each value
    for (int i = 1; i <= n; ++i) {
        scanf("%d", &a[i]);
        pos_value[a[i]] = i;
    }

    vector<pair<int, int>> merges;
    vector<int> answer(q);
    int cnt = n; // current number of sets

    for (int idx = 0; idx < q; ++idx) {
        int l, r;
        scanf("%d %d", &l, &r);
        vector<int> values;
        for (int i = l; i <= r; ++i) {
            values.push_back(a[i]);
        }
        sort(values.begin(), values.end());
        int m = values.size();
        if (m == 0) continue; // not possible since l <= r
        int current_set = pos_value[values[0]];
        for (int j = 1; j < m; ++j) {
            int next_set = pos_value[values[j]];
            ++cnt;
            merges.push_back({current_set, next_set});
            current_set = cnt; // new set ID
        }
        answer[idx] = current_set;
    }

    printf("%d\n", cnt);
    for (auto& p : merges) {
        printf("%d %d\n", p.first, p.second);
    }
    for (int i = 0; i < q; ++i) {
        printf("%d ", answer[i]);
    }
    printf("\n");
    return 0;
}
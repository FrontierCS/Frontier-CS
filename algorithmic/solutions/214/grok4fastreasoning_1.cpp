#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> arr(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> arr[i];
    }
    int x = 3;
    vector<pair<int, int>> operations;
    for (int k = 1; k <= n; k++) {
        int p = -1;
        for (int j = k; j <= n; j++) {
            if (arr[j] == k) {
                p = j;
                break;
            }
        }
        if (p == k) continue;
        int mm = n - k + 1;
        int local_p = p - k + 1;
        vector<int> distance(mm + 1, -1);
        vector<int> previous(mm + 1, -1);
        vector<pair<int, int>> prevmove(mm + 1, make_pair(-1, -1));
        queue<int> q;
        q.push(local_p);
        distance[local_p] = 0;
        while (!q.empty()) {
            int cur = q.front();
            q.pop();
            vector<int> ls = {2, 4};
            for (int ll : ls) {
                if (ll > mm) continue;
                int smin = max(1, cur - ll + 1);
                int smax = min(cur, mm - ll + 1);
                for (int ss = smin; ss <= smax; ss++) {
                    int newcur = 2 * ss + ll - 1 - cur;
                    if (newcur < 1 || newcur > mm) continue;
                    if (distance[newcur] == -1) {
                        distance[newcur] = distance[cur] + 1;
                        previous[newcur] = cur;
                        prevmove[newcur] = make_pair(ss, ll);
                        q.push(newcur);
                    }
                }
            }
        }
        // reconstruct
        vector<pair<int, int>> localops;
        int curr = 1;
        while (curr != local_p) {
            pair<int, int> mv = prevmove[curr];
            localops.push_back(mv);
            curr = previous[curr];
        }
        reverse(localops.begin(), localops.end());
        // apply
        for (auto lsp : localops) {
            int ls = lsp.first;
            int ll = lsp.second;
            int left = k + ls - 1;
            int right = left + ll - 1;
            operations.emplace_back(left, right);
            // reverse arr[left..right]
            reverse(arr.begin() + left, arr.begin() + right + 1);
        }
    }
    cout << x << endl;
    int m = operations.size();
    cout << m << endl;
    for (auto op : operations) {
        cout << op.first << " " << op.second << endl;
    }
    return 0;
}
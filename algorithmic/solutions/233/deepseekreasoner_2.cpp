#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <tuple>

using namespace std;

int main() {
    int t;
    cin >> t;
    while (t--) {
        int n, m;
        cin >> n >> m;
        // read the grid (not used directly, but must be consumed)
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int x;
                cin >> x;
                // ignore, we only need queries
            }
        }
        // interaction
        auto query = [&](int l, int T) -> int {
            cout << "? " << l << " " << T << endl;
            cout.flush();
            int res;
            cin >> res;
            return res;
        };

        // number of times: 1..2n-1
        int totalTimes = 2 * n - 1;
        // current l to query next for each time T (1-indexed)
        vector<int> cur_l(totalTimes + 1, n); // initially we will query l = n
        // min-heap of (value, T, l)
        priority_queue<tuple<int, int, int>, vector<tuple<int, int, int>>, greater<tuple<int, int, int>>> pq;

        // initial queries: f(n, T) for each T
        for (int T = 1; T <= totalTimes; ++T) {
            int val = query(n, T);
            pq.emplace(val, T, n);
        }

        vector<int> ans;
        ans.reserve(m);
        while ((int)ans.size() < m) {
            auto [val, T, l] = pq.top();
            pq.pop();
            ans.push_back(val);
            if (cur_l[T] > 1) {
                cur_l[T]--;
                int new_val = query(cur_l[T], T);
                pq.emplace(new_val, T, cur_l[T]);
            }
        }

        // output answer
        cout << "! ";
        for (int i = 0; i < m; ++i) {
            if (i) cout << " ";
            cout << ans[i];
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}
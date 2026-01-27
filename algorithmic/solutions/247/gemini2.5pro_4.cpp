#include <iostream>
#include <vector>
#include <numeric>
#include <queue>
#include <map>
#include <algorithm>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<long long> a(n), b(n);
    long long sum_a = 0, sum_b = 0;

    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        sum_a += a[i];
    }
    for (int i = 0; i < n; ++i) {
        cin >> b[i];
        sum_b += b[i];
    }

    if (sum_a != sum_b) {
        cout << "No" << endl;
        return 0;
    }

    map<vector<long long>, pair<vector<long long>, pair<int, int>>> parent;
    queue<vector<long long>> q;

    q.push(a);
    parent[a] = {vector<long long>(), {-1, -1}};

    vector<long long> target = b;
    bool found = false;

    while (!q.empty()) {
        vector<long long> u = q.front();
        q.pop();

        if (u == target) {
            found = true;
            break;
        }

        vector<int> deficit_indices;
        vector<int> surplus_indices;
        for (int i = 0; i < n; ++i) {
            if (u[i] < b[i]) {
                deficit_indices.push_back(i);
            } else if (u[i] > b[i]) {
                surplus_indices.push_back(i);
            }
        }

        for (int i : deficit_indices) {
            for (int j : surplus_indices) {
                
                vector<long long> v = u;
                int op_i = min(i, j);
                int op_j = max(i, j);

                long long old_i_val = v[op_i];
                long long old_j_val = v[op_j];

                if (old_i_val == old_j_val - 1) { // No-op check
                    continue;
                }
                
                v[op_i] = old_j_val - 1;
                v[op_j] = old_i_val + 1;

                if (parent.find(v) == parent.end()) {
                    parent[v] = {u, {op_i + 1, op_j + 1}};
                    q.push(v);
                }
            }
        }
    }

    if (found) {
        cout << "Yes" << endl;
        vector<pair<int, int>> ops;
        vector<long long> curr = target;
        while (parent.count(curr) && parent[curr].second.first != -1) {
            ops.push_back(parent[curr].second);
            curr = parent[curr].first;
        }
        reverse(ops.begin(), ops.end());
        cout << ops.size() << endl;
        for (const auto& op : ops) {
            cout << op.first << " " << op.second << endl;
        }
    } else {
        cout << "No" << endl;
    }

    return 0;
}
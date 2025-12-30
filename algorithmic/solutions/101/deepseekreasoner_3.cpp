#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int N, R;
    cin >> N >> R;
    vector<int> U(N), V(N);
    for (int i = 0; i < N; ++i) {
        cin >> U[i] >> V[i];
    }

    const int total = 2 * N + 1;
    vector<int> child1(total, -1), child2(total, -1);
    vector<int> parent(total, -1);
    for (int i = 0; i < N; ++i) {
        child1[i] = U[i];
        child2[i] = V[i];
        parent[U[i]] = i;
        parent[V[i]] = i;
    }

    // compute leaf ranges (in leaf-id space)
    vector<int> leaf_l(total), leaf_r(total);
    vector<int> switch_to_leafid(total, -1);
    vector<int> leaf_switch;
    int leaf_count = 0;
    for (int j = total - 1; j >= 0; --j) {
        if (j >= N) {   // leaf
            leaf_l[j] = leaf_r[j] = leaf_count;
            switch_to_leafid[j] = leaf_count;
            leaf_switch.push_back(j);
            ++leaf_count;
        } else {
            int c1 = child1[j], c2 = child2[j];
            leaf_l[j] = min(leaf_l[c1], leaf_l[c2]);
            leaf_r[j] = max(leaf_r[c1], leaf_r[c2]);
        }
    }

    vector<int> gate_type(N, -1);   // 0 = AND, 1 = OR
    queue<int> q;
    q.push(0);

    while (!q.empty()) {
        int i = q.front(); q.pop();

        // build leaf values for this query
        vector<char> leaf_val(leaf_count, '0');

        int left = child1[i], right = child2[i];
        // left subtree -> 0
        for (int id = leaf_l[left]; id <= leaf_r[left]; ++id)
            leaf_val[id] = '0';
        // right subtree -> 1
        for (int id = leaf_r[right]; id >= leaf_l[right]; --id) // iterate normally
            leaf_val[id] = '1';

        // set sibling subtrees of ancestors
        int a = i;
        while (a != 0) {
            int p = parent[a];
            int sibling = (a == child1[p]) ? child2[p] : child1[p];
            char v = (gate_type[p] == 0) ? '1' : '0';   // AND needs 1, OR needs 0
            for (int id = leaf_l[sibling]; id <= leaf_r[sibling]; ++id)
                leaf_val[id] = v;
            a = p;
        }

        // construct the full query string
        string s(total, '0');
        for (int j = N; j < total; ++j)
            s[j] = leaf_val[switch_to_leafid[j]];

        cout << "? " << s << endl;
        int response;
        cin >> response;
        gate_type[i] = (response == 0) ? 0 : 1;

        if (left < N) q.push(left);
        if (right < N) q.push(right);
    }

    string ans(N, '&');
    for (int i = 0; i < N; ++i)
        if (gate_type[i] == 1)
            ans[i] = '|';
    cout << "! " << ans << endl;

    return 0;
}
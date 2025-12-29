#include <bits/stdc++.h>
using namespace std;

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        auto query = [&](const vector<int>& subset) -> int {
            string s(n, '0');
            for (int i : subset) {
                s[i] = '1';
            }
            cout << "? " << s << endl;
            cout.flush();
            int res;
            cin >> res;
            return res;
        };
        function<bool(vector<int>)> is_connected = [&](vector<int> nodes) -> bool {
            int m = nodes.size();
            if (m <= 1) return true;
            int half = m / 2;
            vector<int> left(nodes.begin(), nodes.begin() + half);
            vector<int> right(nodes.begin() + half, nodes.end());
            int q_L = query(left);
            int q_R = query(right);
            vector<int> whole_nodes = nodes; // for query(Q)
            int q_Q = query(whole_nodes);
            int s = q_L + q_R - q_Q;
            bool linked;
            if (s >= 2) {
                linked = true;
            } else {
                int e_L = q_L;
                int e_R = q_R;
                linked = (e_L > 0 && e_R > 0);
            }
            bool left_conn = is_connected(left);
            bool right_conn = is_connected(right);
            return left_conn && right_conn && linked;
        };
        vector<int> all(n);
        iota(all.begin(), all.end(), 0);
        bool conn = is_connected(all);
        cout << "! " << (conn ? 1 : 0) << endl;
        cout.flush();
    }
    return 0;
}
#include <iostream>
#include <vector>
#include <queue>
#include <bitset>
#include <string>
#include <algorithm>

using namespace std;

const int MAXN = 8000;
const int MAXLEAVES = MAXN + 1;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, R;
    cin >> N >> R;

    vector<int> U(N), V(N);
    for (int i = 0; i < N; ++i) {
        cin >> U[i] >> V[i];
    }

    vector<int> parent_gate(2 * N + 1, -1);
    for (int i = 0; i < N; ++i) {
        parent_gate[U[i]] = i;
        parent_gate[V[i]] = i;
    }

    vector<bitset<MAXLEAVES>> leaf_bits(2 * N + 1);
    for (int j = N; j <= 2 * N; ++j) {
        leaf_bits[j].set(j - N);
    }
    for (int j = N - 1; j >= 0; --j) {
        leaf_bits[j] = leaf_bits[U[j]] | leaf_bits[V[j]];
    }

    vector<char> ans(N);
    vector<bool> known(N, false);
    queue<int> q;

    auto construct_query = [&](int i) -> string {
        bitset<MAXLEAVES> force_one;
        force_one |= leaf_bits[V[i]];

        int current = i;
        while (parent_gate[current] != -1) {
            int p = parent_gate[current];
            int other = (U[p] == current ? V[p] : U[p]);
            if (ans[p] == '&') {
                force_one |= leaf_bits[other];
            }
            current = p;
        }

        string s(2 * N + 1, '0');
        for (int j = N; j <= 2 * N; ++j) {
            if (force_one[j - N]) {
                s[j] = '1';
            }
        }
        return s;
    };

    {
        bitset<MAXLEAVES> force_one;
        force_one |= leaf_bits[V[0]];
        string s(2 * N + 1, '0');
        for (int j = N; j <= 2 * N; ++j) {
            if (force_one[j - N]) {
                s[j] = '1';
            }
        }
        cout << "? " << s << endl;
        int res;
        cin >> res;
        ans[0] = (res == 0 ? '&' : '|');
        known[0] = true;
        q.push(0);
    }

    while (!q.empty()) {
        int i = q.front();
        q.pop();
        for (int child_switch : {U[i], V[i]}) {
            if (child_switch < N && !known[child_switch]) {
                string s = construct_query(child_switch);
                cout << "? " << s << endl;
                int res;
                cin >> res;
                ans[child_switch] = (res == 0 ? '&' : '|');
                known[child_switch] = true;
                q.push(child_switch);
            }
        }
    }

    string result(N, ' ');
    for (int i = 0; i < N; ++i) {
        result[i] = ans[i];
    }
    cout << "! " << result << endl;

    return 0;
}
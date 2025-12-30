#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;

    vector<int> val_at_pos(n + 1, 0);   // known value at each position (0 = unknown)
    vector<int> pos_of_val(n + 1, 0);   // known position of each value (0 = unknown)
    vector<int> undetermined;

    // Step 1: find positions of values 1 and 2 using n queries
    for (int i = 1; i <= n; ++i) {
        cout << 0;
        for (int j = 1; j <= n; ++j) {
            if (j == i) cout << " 2";
            else cout << " 1";
        }
        cout << endl;
        cout.flush();

        int ans;
        cin >> ans;
        if (ans == 0) {
            // position i has value 1
            val_at_pos[i] = 1;
            pos_of_val[1] = i;
        } else if (ans == 2) {
            // position i has value 2
            val_at_pos[i] = 2;
            pos_of_val[2] = i;
        }
        // if ans == 1, the position has neither 1 nor 2
    }

    // collect undetermined positions
    for (int i = 1; i <= n; ++i) {
        if (val_at_pos[i] == 0) {
            undetermined.push_back(i);
        }
    }

    // Step 2: determine positions of values 3 .. n
    for (int v = 3; v <= n; ++v) {
        if (undetermined.empty()) break;
        int m = undetermined.size();
        if (m == 1) {
            // only one undetermined position left
            int pos = undetermined[0];
            val_at_pos[pos] = v;
            pos_of_val[v] = pos;
            undetermined.pop_back();
            continue;
        }

        int d = 0;
        while ((1 << d) < m) ++d;   // d = ceil(log2(m))

        int idx_v = 0;   // index (in undetermined) of the position that holds value v
        for (int bit = 0; bit < d; ++bit) {
            // build query for this bit
            vector<int> q(n + 1, 0);
            // set known positions to their correct values
            for (int i = 1; i <= n; ++i) {
                if (val_at_pos[i] != 0) {
                    q[i] = val_at_pos[i];
                }
            }
            // set undetermined positions: those with bit set get v, others get 1 (safe filler)
            for (int j = 0; j < m; ++j) {
                int i = undetermined[j];
                if ((j >> bit) & 1) {
                    q[i] = v;
                } else {
                    q[i] = 1;
                }
            }

            cout << 0;
            for (int i = 1; i <= n; ++i) {
                cout << " " << q[i];
            }
            cout << endl;
            cout.flush();

            int ans;
            cin >> ans;
            if (ans == v) {   // the bit is 1
                idx_v |= (1 << bit);
            }
            // if ans == v-1, the bit is 0
        }

        // now idx_v is the index of the position that holds value v
        int pos = undetermined[idx_v];
        val_at_pos[pos] = v;
        pos_of_val[v] = pos;

        // remove this position from undetermined (swap with last and pop)
        swap(undetermined[idx_v], undetermined[m - 1]);
        undetermined.pop_back();
    }

    // output the final permutation
    cout << 1;
    for (int i = 1; i <= n; ++i) {
        cout << " " << val_at_pos[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}
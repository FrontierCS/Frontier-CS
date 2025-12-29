#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<int> p;
vector<int> pos;
vector<pair<int, int>> ops;

void apply_op(int x, int y) {
    if (x <= 0 || y <= 0 || x + y >= n) {
        return;
    }
    ops.push_back({x, y});

    vector<int> temp = p;
    
    // Suffix
    for(int i = 0; i < y; ++i) {
        p[i] = temp[n - y + i];
    }
    // Middle
    for(int i = 0; i < n - x - y; ++i) {
        p[y + i] = temp[x + i];
    }
    // Prefix
    for(int i = 0; i < x; ++i) {
        p[n - x + i] = temp[i];
    }

    for (int i = 0; i < n; ++i) {
        pos[p[i]] = i;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    p.resize(n);
    pos.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
        pos[p[i]] = i;
    }

    if (n == 3) {
        if (p[0] == 2 && p[1] == 1 && p[2] == 3) { // 2 1 3 -> target 2 1 3
             // do nothing
        } else if (p[0] == 3 && p[1] == 1 && p[2] == 2) { // 3 1 2 -> target 2 1 3
            apply_op(1, 1);
        } else if (p[0] == 1 && p[1] == 3 && p[2] == 2) { // 1 3 2 -> target 1 3 2
            // do nothing
        } else if (p[0] == 2 && p[1] == 3 && p[2] == 1) { // 2 3 1 -> target 1 3 2
            apply_op(1, 1);
        } else { // All other cases sort to 1 2 3
            while (p[0] != 1 || p[1] != 2 || p[2] != 3) {
                 if (p[0] == 3) apply_op(1,1);
                 else if (p[0] == 2) apply_op(1,1);
            }
        }
    } else {
        for (int i = 1; i <= n; ++i) {
            int current_pos = pos[i];
            int target_pos = i - 1;

            if (current_pos == target_pos) {
                continue;
            }

            if (current_pos > 0) {
                apply_op(current_pos, 1);
            }
            
            int len_prefix_to_cycle = n - (i - 1);
            if (len_prefix_to_cycle > 1) {
                 apply_op(1, n - len_prefix_to_cycle);
            }
        }
    }


    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.first << " " << op.second << endl;
    }

    return 0;
}
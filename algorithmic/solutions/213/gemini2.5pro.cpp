#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

struct Operation {
    int l, r, d;
};

// Global state to avoid passing a, pos, ops everywhere
int n;
vector<int> a;
vector<int> pos;
vector<Operation> ops;

void do_op(int l, int r, int d) {
    ops.push_back({l, r, d});

    vector<int> segment_vals;
    for (int i = l - 1; i < r; ++i) {
        segment_vals.push_back(a[i]);
    }

    if (d == 0) { // left shift
        int first_val = segment_vals[0];
        for (size_t i = 0; i < segment_vals.size() - 1; ++i) {
            a[l - 1 + i] = segment_vals[i + 1];
            pos[segment_vals[i + 1]] = l + i;
        }
        a[r - 1] = first_val;
        pos[first_val] = r;
    } else { // right shift
        int last_val = segment_vals.back();
        for (size_t i = segment_vals.size() - 1; i > 0; --i) {
            a[l - 1 + i] = segment_vals[i - 1];
            pos[segment_vals[i - 1]] = l + i;
        }
        a[l - 1] = last_val;
        pos[last_val] = l;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;

    a.resize(n);
    pos.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        pos[a[i]] = i + 1;
    }

    if (n == 1) {
        cout << "1 0\n";
        return 0;
    }

    int x = min((int)floor(sqrt(n)) + 2, n);
    if (x <= 1) x = 2;

    for (int i = 1; i <= n; ++i) {
        while (pos[i] != i) {
            int current_pos = pos[i];
            
            if (current_pos - i >= x - 1) {
                // Big jump
                int l = current_pos - x + 1;
                do_op(l, current_pos, 1);
            } else {
                // Small jumps
                int dist = current_pos - i;
                int l, r;
                if (i + x - 1 <= n) {
                    l = i;
                    r = i + x - 1;
                } else {
                    r = n;
                    l = r - x + 1;
                }
                for (int k = 0; k < dist; ++k) {
                    do_op(l, r, 0);
                }
            }
        }
    }

    cout << x << " " << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.l << " " << op.r << " " << op.d << endl;
    }

    return 0;
}
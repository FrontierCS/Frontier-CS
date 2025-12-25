#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int N;
    cin >> N;

    // random permutation of slices
    vector<int> perm(2 * N);
    iota(perm.begin(), perm.end(), 1);
    random_device rd;
    mt19937 g(rd());
    shuffle(perm.begin(), perm.end(), g);

    vector<int> stack;
    vector<bool> paired(2 * N + 1, false);
    vector<bool> in_machine(2 * N + 1, false);
    int distinct = 0;
    int queries = 0;
    const int QUERY_LIMIT = 1000000;

    auto query = [&](int x) -> int {
        cout << "? " << x << endl;
        queries++;
        int r;
        cin >> r;
        in_machine[x] = !in_machine[x];
        distinct = r;
        return r;
    };

    for (int x : perm) {
        if (paired[x]) continue;

        int r = query(x);
        if (queries > QUERY_LIMIT) return 0;

        if (r > distinct) {                     // new mineral type
            stack.push_back(x);
            distinct = r;
        } else {                                // partner is in the stack
            int k = stack.size();
            int l = 0, r_idx = k - 1;

            // invariant: device contains stack[l..r_idx] and x
            while (l < r_idx) {
                int mid = (l + r_idx) / 2;

                // remove left half [l..mid]
                for (int i = l; i <= mid; ++i) {
                    r = query(stack[i]);
                }
                int C = r;                      // distinct count after removal
                int rightSize = r_idx - mid;    // size of [mid+1..r_idx]

                if (C == rightSize + 1) {       // partner in left half
                    // remove right half [mid+1..r_idx]
                    for (int i = mid + 1; i <= r_idx; ++i) {
                        r = query(stack[i]);
                    }
                    // now device contains only x
                    // reinsert left half
                    for (int i = l; i <= mid; ++i) {
                        r = query(stack[i]);
                    }
                    // device now contains stack[l..mid] and x
                    r_idx = mid;
                } else {                        // partner in right half
                    l = mid + 1;
                    // device already contains stack[mid+1..r_idx] and x
                }
            }

            int partner = stack[l];
            cout << "! " << x << " " << partner << endl;
            paired[x] = paired[partner] = true;

            // remove x and partner from device if present
            if (in_machine[x]) query(x);
            if (in_machine[partner]) query(partner);

            // ensure all other stack slices are in the device
            for (int i = 0; i < (int)stack.size(); ++i) {
                int y = stack[i];
                if (y == partner) continue;
                if (!in_machine[y]) query(y);
            }

            // remove partner from the stack
            for (int i = 0; i < (int)stack.size(); ++i) {
                if (stack[i] == partner) {
                    swap(stack[i], stack.back());
                    break;
                }
            }
            stack.pop_back();
            distinct = stack.size();
        }
    }

    return 0;
}
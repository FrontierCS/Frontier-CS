#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstring>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;

        // compute max queries = 2 * ceil(log_{1.116} n)
        double log1_116 = log(1.116);
        int k = ceil(log(n) / log1_116);
        int maxQ = 2 * k;

        // mask for each student: bit 0..3 represent states (0,0),(0,1),(1,0),(1,1)
        vector<uint8_t> mask(n + 1, 0b1111);
        int count_possible = n;
        int queries = 0;

        while (count_possible > 2 && queries < maxQ) {
            // find current min and max possible student
            int low = -1, high = -1;
            for (int i = 1; i <= n; ++i) {
                if (mask[i]) {
                    low = i;
                    break;
                }
            }
            for (int i = n; i >= 1; --i) {
                if (mask[i]) {
                    high = i;
                    break;
                }
            }
            int mid = (low + high) / 2;
            int l = low, r = mid;
            if (l > r) r = l;

            // ask query
            cout << "? " << l << " " << r << endl;
            cout.flush();
            int x;
            cin >> x;
            int s = x - (r - l);   // s is 0 or 1
            queries++;

            // update masks
            vector<uint8_t> new_mask(n + 1, 0);
            int new_count = 0;
            for (int A = 1; A <= n; ++A) {
                if (mask[A] == 0) continue;
                int T = (l <= A && A <= r) ? 1 : 0;
                uint8_t old = mask[A];
                uint8_t new_bits = 0;
                // iterate over the 4 states
                for (int state = 0; state < 4; ++state) {
                    if ((old >> state) & 1) {
                        int b = state & 1;
                        if ((T ^ b) == s) {
                            // generate next states according to transition rules
                            if (state == 0) {           // (0,0) -> (0,1)
                                new_bits |= (1 << 1);
                            } else if (state == 1) {    // (0,1) -> (1,0) or (1,1)
                                new_bits |= (1 << 2) | (1 << 3);
                            } else if (state == 2) {    // (1,0) -> (0,0) or (0,1)
                                new_bits |= (1 << 0) | (1 << 1);
                            } else if (state == 3) {    // (1,1) -> (1,0)
                                new_bits |= (1 << 2);
                            }
                        }
                    }
                }
                if (new_bits) {
                    new_mask[A] = new_bits;
                    new_count++;
                }
            }
            mask = move(new_mask);
            count_possible = new_count;
        }

        // collect candidates
        vector<int> candidates;
        for (int i = 1; i <= n; ++i) {
            if (mask[i]) candidates.push_back(i);
        }

        // output at most two guesses
        bool found = false;
        for (int i = 0; i < min(2, (int)candidates.size()); ++i) {
            cout << "! " << candidates[i] << endl;
            cout.flush();
            int y;
            cin >> y;
            if (y == 1) {
                found = true;
                break;
            }
        }
        // end test case
        cout << "#" << endl;
        cout.flush();
    }
    return 0;
}
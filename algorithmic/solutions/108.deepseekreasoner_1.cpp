#include <iostream>
#include <vector>
#include <cmath>
using namespace std;

int n, m, N;
int cur_free;
int rot[105]; // net rotations applied (mod N)

void apply_rotation(int x, int d) {
    cout << "? " << x << " " << d << endl;
    cin >> cur_free;
    rot[x] = (rot[x] + d + N) % N;
}

bool alignment_test(int i) {
    // Test whether ring i is currently aligned with ring 0.
    // Returns true if rotating ring 0 and ring i give the same Δ.
    int f0 = cur_free;
    apply_rotation(0, 1);
    int delta0 = cur_free - f0;
    apply_rotation(0, -1);          // back
    apply_rotation(i, 1);
    int delta_i = cur_free - f0;
    apply_rotation(i, -1);          // back
    return delta0 == delta_i;
}

int main() {
    cin >> n >> m;
    N = n * m;
    for (int i = 0; i < n; ++i) rot[i] = 0;

    // Get initial free value without changing configuration
    apply_rotation(0, 1);
    apply_rotation(0, -1);

    vector<int> p(n, 0);   // p[1]..p[n-1] will hold the answer

    for (int i = 1; i < n; ++i) {
        // Hill climbing to find a local maximum of free
        int t = 0, f = cur_free;
        int t_max = 0, f_max = f;
        int dir = 1;           // first try clockwise
        int steps = 0;
        while (steps < 100) {
            apply_rotation(i, dir);
            t += dir;
            ++steps;
            if (cur_free > f_max) {
                f_max = cur_free;
                t_max = t;
            }
            if (cur_free <= f) {
                // reached a decrease, stop climbing
                int diff = (t_max - t) % N;
                if (diff != 0) {
                    int d2 = diff > 0 ? 1 : -1;
                    for (int k = 0; k < abs(diff); ++k)
                        apply_rotation(i, d2);
                    t = t_max;
                }
                break;
            }
            f = cur_free;
        }
        // If we stopped because of step limit, move to t_max
        if (steps == 100) {
            int diff = (t_max - t) % N;
            if (diff != 0) {
                int d2 = diff > 0 ? 1 : -1;
                for (int k = 0; k < abs(diff); ++k)
                    apply_rotation(i, d2);
                t = t_max;
            }
        }

        // Check alignment at the peak
        bool aligned = alignment_test(i);
        int t_align = t_max;
        if (!aligned) {
            // Search nearby offsets (±1, ±2, ..., ±m)
            int original_t = t_max;
            bool found = false;
            for (int k = 1; k <= m; ++k) {
                // try +k
                for (int step = 0; step < k; ++step) apply_rotation(i, 1);
                if (alignment_test(i)) {
                    t_align = (original_t + k) % N;
                    found = true;
                    break;
                }
                for (int step = 0; step < k; ++step) apply_rotation(i, -1); // back
                // try -k
                for (int step = 0; step < k; ++step) apply_rotation(i, -1);
                if (alignment_test(i)) {
                    t_align = (original_t - k + N) % N;
                    found = true;
                    break;
                }
                for (int step = 0; step < k; ++step) apply_rotation(i, 1); // back
            }
            if (!found) {
                // Fallback (should not happen with proper constraints)
                t_align = original_t;
            }
        }

        p[i] = (N - t_align) % N;
        // Ring i is now left aligned with ring 0 (no need to move back).
    }

    // Output the result
    cout << "!";
    for (int i = 1; i < n; ++i)
        cout << " " << p[i];
    cout << endl;

    return 0;
}
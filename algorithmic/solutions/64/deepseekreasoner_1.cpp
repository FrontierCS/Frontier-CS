#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdint>
#include <string>

using namespace std;

const int K = 100000;  // beam width

struct Entry {
    int64_t diff;
    uint64_t mask_low;
    uint64_t mask_high;
};

int main() {
    int n;
    int64_t T;
    cin >> n >> T;
    vector<int64_t> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }

    // If T is 0, output all zeros
    if (T == 0) {
        cout << string(n, '0') << endl;
        return 0;
    }

    // Create array with original indices and sort descending
    vector<pair<int64_t, int>> items;
    for (int i = 0; i < n; i++) {
        items.push_back({a[i], i});
    }
    sort(items.begin(), items.end(), [](const pair<int64_t, int>& x, const pair<int64_t, int>& y) {
        return x.first > y.first;
    });

    vector<Entry> current;
    current.push_back({T, 0, 0});

    for (const auto& item : items) {
        int64_t val = item.first;
        int idx = item.second;
        vector<Entry> next;
        next.reserve(current.size() * 2);

        for (const auto& e : current) {
            // Exclude current item
            next.push_back(e);
            // Include current item
            int64_t new_diff = e.diff - val;
            uint64_t new_low = e.mask_low;
            uint64_t new_high = e.mask_high;
            if (idx < 64) {
                new_low |= (1ULL << idx);
            } else {
                new_high |= (1ULL << (idx - 64));
            }
            next.push_back({new_diff, new_low, new_high});
            // Early exit if exact solution found
            if (new_diff == 0) {
                string ans(n, '0');
                for (int i = 0; i < n; i++) {
                    if (i < 64) {
                        if (new_low & (1ULL << i)) ans[i] = '1';
                    } else {
                        if (new_high & (1ULL << (i - 64))) ans[i] = '1';
                    }
                }
                cout << ans << endl;
                return 0;
            }
        }

        // Prune: keep only the K smallest absolute differences, unique diff values
        sort(next.begin(), next.end(), [](const Entry& a, const Entry& b) {
            int64_t abs_a = a.diff < 0 ? -a.diff : a.diff;
            int64_t abs_b = b.diff < 0 ? -b.diff : b.diff;
            if (abs_a != abs_b) return abs_a < abs_b;
            return a.diff < b.diff;
        });

        current.clear();
        int64_t prev_diff = 0;
        bool first = true;
        for (const auto& e : next) {
            if (!first && e.diff == prev_diff) continue;
            first = false;
            prev_diff = e.diff;
            current.push_back(e);
            if (current.size() >= K) break;
        }
    }

    // Choose the best entry (closest to zero)
    Entry best = current[0];
    int64_t best_abs = best.diff < 0 ? -best.diff : best.diff;
    for (const auto& e : current) {
        int64_t abs_e = e.diff < 0 ? -e.diff : e.diff;
        if (abs_e < best_abs) {
            best_abs = abs_e;
            best = e;
        }
    }

    // Output the binary string
    string ans(n, '0');
    for (int i = 0; i < n; i++) {
        if (i < 64) {
            if (best.mask_low & (1ULL << i)) ans[i] = '1';
        } else {
            if (best.mask_high & (1ULL << (i - 64))) ans[i] = '1';
        }
    }
    cout << ans << endl;

    return 0;
}
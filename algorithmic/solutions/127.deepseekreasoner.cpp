#include <iostream>
#include <vector>
#include <cassert>

using namespace std;

const int MAXN = 200000;

int n;
bool queried[MAXN] = {false};
int left_cnt[MAXN], right_cnt[MAXN];

int query(int i) {
    if (queried[i]) {
        return left_cnt[i] + right_cnt[i];
    }
    cout << "? " << i << endl;
    cout.flush();
    cin >> left_cnt[i] >> right_cnt[i];
    queried[i] = true;
    return left_cnt[i] + right_cnt[i];
}

// Returns an index in [l, r] with S < threshold, or -1 if none.
// Uses binary search with recursion, but for small intervals does linear scan.
int find_prize_with_S_less_than(int threshold, int l, int r) {
    if (l > r) return -1;
    // If interval is small, linear scan.
    if (r - l + 1 <= 10) {
        for (int i = l; i <= r; ++i) {
            int s = query(i);
            if (s < threshold) {
                return i;
            }
        }
        return -1;
    }
    int m = (l + r) / 2;
    int s = query(m);
    if (s < threshold) {
        return m;
    }
    // s >= threshold
    int res = -1;
    if (left_cnt[m] > 0) {
        res = find_prize_with_S_less_than(threshold, l, m-1);
    }
    if (res == -1 && right_cnt[m] > 0) {
        res = find_prize_with_S_less_than(threshold, m+1, r);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    if (n == 1) {
        cout << "! 0" << endl;
        return 0;
    }
    // Query endpoints to get an estimate of E (S for cheap prizes)
    int s0 = query(0);
    if (s0 == 0) {
        cout << "! 0" << endl;
        return 0;
    }
    int sn = query(n-1);
    if (sn == 0) {
        cout << "! " << n-1 << endl;
        return 0;
    }
    int E = max(s0, sn);
    int current = find_prize_with_S_less_than(E, 0, n-1);
    if (current == -1) {
        // Fallback: should not happen
        // try linear scan
        for (int i = 0; i < n; ++i) {
            if (query(i) == 0) {
                cout << "! " << i << endl;
                return 0;
            }
        }
        // still not found, guess
        cout << "! 0" << endl;
        return 0;
    }
    while (true) {
        int s = query(current);
        if (s == 0) {
            cout << "! " << current << endl;
            return 0;
        }
        int new_current = -1;
        if (left_cnt[current] > 0) {
            new_current = find_prize_with_S_less_than(s, 0, current-1);
        }
        if (new_current == -1 && right_cnt[current] > 0) {
            new_current = find_prize_with_S_less_than(s, current+1, n-1);
        }
        if (new_current == -1) {
            // Should not happen, fallback
            for (int i = 0; i < n; ++i) {
                if (!queried[i]) {
                    if (query(i) == 0) {
                        cout << "! " << i << endl;
                        return 0;
                    }
                }
            }
            // still not found
            cout << "! " << current << endl;
            return 0;
        }
        current = new_current;
    }
    return 0;
}
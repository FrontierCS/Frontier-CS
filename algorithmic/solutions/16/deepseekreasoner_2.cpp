#include <iostream>
#include <map>
#include <algorithm>
using namespace std;

int n;
map<pair<int, int>, int> cache;
int queries = 0;

// ask distance between x and y, with caching
int ask(int x, int y) {
    if (x > y) swap(x, y);
    if (cache.count({x, y})) return cache[{x, y}];
    if (queries >= 500) {
        // should not happen, but to be safe we exit
        // (problem guarantees enough queries)
    }
    cout << "? " << x << " " << y << endl;
    int d;
    cin >> d;
    cache[{x, y}] = d;
    queries++;
    return d;
}

// return vertex when moving delta steps from x (delta can be negative)
int mod_add(int x, int delta) {
    int res = (x - 1 + delta) % n;
    if (res < 0) res += n;
    return res + 1;
}

// try to find the chord using vertex r as reference
// returns {-1,-1} if no anomaly found
pair<int, int> find_chord(int r) {
    // ---------- Step 1: find first anomaly clockwise ----------
    int step = 1;
    int prev_offset = 0;
    int hi_offset = -1;
    while (prev_offset < n / 2) {
        int offset = prev_offset + step;
        if (offset > n / 2) offset = n / 2;
        int x = mod_add(r, offset);
        int d = ask(r, x);
        int C = min(offset, n - offset); // cycle distance
        if (d < C) {
            hi_offset = offset;
            break;
        }
        if (offset == n / 2) break;
        prev_offset = offset;
        step *= 2;
    }
    if (hi_offset == -1) {
        return {-1, -1}; // no anomaly found
    }

    // binary search for the first offset with d < C
    int lo_offset = prev_offset;
    int p_offset = hi_offset;
    while (lo_offset < hi_offset) {
        int mid = (lo_offset + hi_offset) / 2;
        int x = mod_add(r, mid);
        int d = ask(r, x);
        int C = min(mid, n - mid);
        if (d < C) {
            hi_offset = mid;
            p_offset = mid;
        } else {
            lo_offset = mid + 1;
        }
    }
    int p = mod_add(r, p_offset);

    // ---------- Step 2: find the endpoint (minimizer) ----------
    int L_offset = p_offset;
    int cur_offset = L_offset;
    int step2 = 1;
    int last_d = ask(r, mod_add(r, cur_offset));
    while (true) {
        int next_offset = cur_offset + step2;
        if (next_offset > n / 2) break;
        int x = mod_add(r, next_offset);
        int d_val = ask(r, x);
        if (d_val > last_d) break;
        last_d = d_val;
        cur_offset = next_offset;
        step2 *= 2;
    }
    int R_offset = cur_offset + step2;
    if (R_offset > n / 2) R_offset = n / 2;

    // ternary search for the minimum in [L_offset, R_offset]
    int l = L_offset, r_end = R_offset;
    while (r_end - l > 5) {
        int m1 = l + (r_end - l) / 3;
        int m2 = r_end - (r_end - l) / 3;
        int d1 = ask(r, mod_add(r, m1));
        int d2 = ask(r, mod_add(r, m2));
        if (d1 < d2) {
            r_end = m2 - 1;
        } else if (d1 > d2) {
            l = m1 + 1;
        } else {
            l = m1;
            r_end = m2 - 1;
        }
    }
    int best_offset = l;
    int best_d = ask(r, mod_add(r, l));
    for (int off = l + 1; off <= r_end; ++off) {
        int d_val = ask(r, mod_add(r, off));
        if (d_val < best_d) {
            best_d = d_val;
            best_offset = off;
        }
    }
    int e = mod_add(r, best_offset); // one endpoint
    int d_e = best_d;

    // ---------- Step 3: find the other endpoint ----------
    int cand_dist = d_e - 1;
    int f1 = mod_add(r, cand_dist);
    int f2 = mod_add(r, -cand_dist);
    if (ask(e, f1) == 1) {
        return {e, f1};
    } else {
        return {e, f2};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        cin >> n;
        cache.clear();
        queries = 0;
        bool found = false;
        // try reference vertices 1,2,3,... until successful
        for (int r = 1; r <= 10; ++r) {
            auto chord = find_chord(r);
            if (chord.first != -1) {
                int u = chord.first, v = chord.second;
                if (u > v) swap(u, v);
                cout << "! " << u << " " << v << endl;
                int resp;
                cin >> resp;
                if (resp == -1) return 0; // incorrect guess
                found = true;
                break;
            }
        }
        if (!found) {
            // fallback (should not happen with given constraints)
            // guess an arbitrary chord (1,3) and exit
            cout << "! 1 3" << endl;
            int resp;
            cin >> resp;
            if (resp == -1) return 0;
        }
    }
    return 0;
}
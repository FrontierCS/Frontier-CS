#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<int> a;
vector<pair<int, int>> ops;
int x;
int L1, L2;

vector<int> pos;

void find_pos_map() {
    pos.assign(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pos[a[i]] = i + 1;
    }
}

void do_reverse(int l, int r) {
    if (l < 1 || r > n || l >= r) return;
    ops.push_back({l, r});
    reverse(a.begin() + l - 1, a.begin() + r);
}

void apply_prefix_rev(int len) {
    if (len <= 1 || len > n) return;
    do_reverse(1, len);
    find_pos_map();
}

void move_val_to_pos1(int val) {
    int p = pos[val];
    if (p == 1) return;

    if (p == L1 || p == L2) {
        apply_prefix_rev(p);
    } else {
        if (L1 > 0) apply_prefix_rev(L1);
        p = pos[val];
        if (p == L1 || p == L2) {
            apply_prefix_rev(p);
        } else {
            if (L2 > 0) apply_prefix_rev(L2);
            p = pos[val];
            apply_prefix_rev(p);
        }
    }
}

void move_val_from_pos1(int val, int target_pos) {
    if (target_pos == 1) return;

    if (target_pos == L1 || target_pos == L2) {
        apply_prefix_rev(target_pos);
    } else {
        if (L1 > 0) apply_prefix_rev(L1);
        int p = pos[val];
        if (p == target_pos) return;
        
        if (p == L1 || p == L2) {
             // After rev(1,L1), val is at L1. To move it to target_pos,
             // we need to move it from L1.
             // This is rev(1,L1) composed with rev(1,target_pos).
             // Equivalent to moving from 1 to target_pos, then from target_pos to L1.
             // Let's bring it back to 1 first.
             apply_prefix_rev(p); // val is at 1 again
        }
        
        // From 1 to target_pos
        if (L2 > 0) apply_prefix_rev(L2);
        p = pos[val];
        if (p != target_pos) {
            apply_prefix_rev(p);
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    a.resize(n);
    int mismatch_parity_count = 0;
    vector<int> initial_pos(n + 1);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        initial_pos[a[i]] = i + 1;
    }

    if (n == 1) {
        cout << 1 << endl;
        cout << 0 << endl;
        return 0;
    }

    for (int i = 1; i <= n; ++i) {
        if ((initial_pos[i] % 2) != (i % 2)) {
            mismatch_parity_count++;
        }
    }
    
    if (mismatch_parity_count > 0) { // need even length reversals -> x is odd
        x = (n % 2 != 0) ? n : n - 1;
        if (x > n) x = n-1;
    } else { // need odd length reversals -> x is even
        x = (n % 2 == 0) ? n : n - 1;
         if (x > n) x = n-1;
    }

    if (x % 2 == 0 && mismatch_parity_count > 0) x--;
    if (x % 2 != 0 && mismatch_parity_count == 0) x--;

    while (x + 1 > n && x > 2) {
        x -= 2;
    }
    if (x <= 0) x = 2;


    L1 = x - 1;
    L2 = x + 1;
    
    find_pos_map();

    for (int i = n; i >= 1; --i) {
        if (pos[i] == i) continue;
        move_val_to_pos1(i);
        move_val_from_pos1(i, i);
    }

    cout << x << endl;
    cout << ops.size() << endl;
    for (const auto& p : ops) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}
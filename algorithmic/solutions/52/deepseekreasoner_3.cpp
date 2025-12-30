#include <bits/stdc++.h>
using namespace std;

int n, l1, l2;
vector<int> cur_pos, cur_idx; // 1-indexed

// interactivity functions
int ask(int l, int r) {
    cout << "1 " << l << " " << r << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

void do_swap(int a, int b) {
    if (a == b) return;
    cout << "2 " << a << " " << b << endl;
    cout.flush();
    int confirm;
    cin >> confirm; // should be 1
    // update internal arrays
    int orig_a = cur_idx[a];
    int orig_b = cur_idx[b];
    swap(cur_idx[a], cur_idx[b]);
    cur_pos[orig_a] = b;
    cur_pos[orig_b] = a;
}

void answer(const vector<int>& p) {
    cout << "3";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
    cout.flush();
}

int main() {
    cin >> n >> l1 >> l2;
    if (n == 1) {
        vector<int> p = {0, 1};
        answer(p);
        return 0;
    }

    cur_pos.resize(n+1);
    cur_idx.resize(n+1);
    for (int i = 1; i <= n; ++i) {
        cur_pos[i] = i;
        cur_idx[i] = i;
    }

    // Step 1: find the two endpoints (min and max)
    vector<int> endpoints;
    for (int orig = 1; orig <= n; ++orig) {
        int old_pos = cur_pos[orig];
        if (old_pos != 1) {
            do_swap(old_pos, 1);
        }
        // now orig is at position 1
        int x = ask(2, n);
        if (x == 1) {
            endpoints.push_back(orig);
        }
        // swap back if needed
        if (old_pos != 1) {
            do_swap(1, old_pos);
        }
    }
    // endpoints should contain exactly two indices
    int min_orig = endpoints[0];
    int max_orig = endpoints[1]; // not directly used

    // Step 2: find the element consecutive to min_orig (min+1)
    // place min_orig at position 1
    if (cur_pos[min_orig] != 1) {
        do_swap(cur_pos[min
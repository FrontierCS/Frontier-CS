#include <bits/stdc++.h>
using namespace std;

pair<int, int> find_leftmost(int pl, int pr, int current_G, int extra_right, int max_K) {
    int leftt = pl;
    int rightt = pr;
    while (leftt <= rightt) {
        int mid = leftt + (rightt - leftt) / 2;
        cout << "? " << mid << '\n';
        cout.flush();
        int aa0, aa1;
        cin >> aa0 >> aa1;
        int kk = aa0 + aa1;
        int num_sub_l = aa0 - current_G;
        if (num_sub_l > 0) {
            rightt = mid - 1;
        } else {
            if (kk < max_K) {
                return {mid, kk};
            } else {
                leftt = mid + 1;
            }
        }
    }
    return {-1, -1};
}

int main() {
    int n;
    cin >> n;
    int num_init = min(501, n);
    int max_k = -1;
    int b_pos = -1;
    int b_a0 = -1, b_a1 = -1;
    bool found_diamond = false;
    int diamond_pos = -1;
    for (int i = 0; i < num_init; i++) {
        cout << "? " << i << '\n';
        cout.flush();
        int aa0, aa1;
        cin >> aa0 >> aa1;
        int kk = aa0 + aa1;
        if (kk == 0) {
            found_diamond = true;
            diamond_pos = i;
            break;
        }
        if (kk > max_k) {
            max_k = kk;
            b_pos = i;
            b_a0 = aa0;
            b_a1 = aa1;
        }
    }
    if (found_diamond) {
        cout << "! " << diamond_pos << '\n';
        cout.flush();
        return 0;
    }
    int num_l = b_a0;
    int num_r = b_a1;
    vector<pair<int, int>> goods;
    // left
    if (num_l > 0) {
        int curr_pl = 0;
        int curr_G = 0;
        int extra_r = b_a1;
        int search_pr = b_pos - 1;
        if (search_pr >= curr_pl) {
            for (int j = 0; j < num_l; j++) {
                auto [pos, kk] = find_leftmost(curr_pl, search_pr, curr_G, extra_r, max_k);
                if (pos == -1) break;
                goods.emplace_back(pos, kk);
                curr_pl = pos + 1;
                curr_G++;
                if (curr_pl > search_pr) break;
            }
        }
    }
    // right
    if (num_r > 0) {
        int curr_pl = b_pos + 1;
        int search_pr = n - 1;
        int curr_G = num_l;
        int extra_r = 0;
        if (curr_pl <= search_pr) {
            for (int j = 0; j < num_r; j++) {
                auto [pos, kk] = find_leftmost(curr_pl, search_pr, curr_G, extra_r, max_k);
                if (pos == -1) break;
                goods.emplace_back(pos, kk);
                curr_pl = pos + 1;
                curr_G++;
                if (curr_pl > search_pr) break;
            }
        }
    }
    // find diamond
    diamond_pos = 0;  // default
    for (auto& p : goods) {
        if (p.second == 0) {
            diamond_pos = p.first;
            break;
        }
    }
    cout << "! " << diamond_pos << '\n';
    cout.flush();
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> ans(n + 1, 0);
    if (n == 1) {
        cout << "! 1" << endl;
        return 0;
    }
    if (n == 2) {
        cout << "? 1 2" << endl;
        cout.flush();
        char c;
        cin >> c;
        if (c == '>') {
            ans[1] = 2;
            ans[2] = 1;
        } else {
            ans[1] = 1;
            ans[2] = 2;
        }
        cout << "! " << ans[1] << " " << ans[2] << endl;
        return 0;
    }
    // n >= 3
    int pp[3];
    pp[0] = max(1, n - 2);
    pp[1] = n - 1;
    pp[2] = n;
    bool gt[3][3] = {};
    for (int i = 0; i < 3; ++i) {
        for (int j = i + 1; j < 3; ++j) {
            cout << "? " << pp[i] << " " << pp[j] << endl;
            cout.flush();
            char c;
            cin >> c;
            gt[i][j] = (c == '>');
            gt[j][i] = !gt[i][j];
        }
    }
    int wins[3] = {0};
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            if (i != j && gt[i][j]) ++wins[i];
        }
    }
    int max_i = 0;
    for (int i = 1; i < 3; ++i) {
        if (wins[i] > wins[max_i]) max_i = i;
    }
    int max_p = pp[max_i];
    ans[max_p] = n;
    vector<int> other_idx;
    for (int i = 0; i < 3; ++i) {
        if (i != max_i) other_idx.push_back(i);
    }
    int i1 = other_idx[0], i2 = other_idx[1];
    bool g12 = gt[i1][i2];
    int current_max_pos, current_min_pos;
    if (g12) {
        current_max_pos = pp[i1];
        current_min_pos = pp[i2];
    } else {
        current_max_pos = pp[i2];
        current_min_pos = pp[i1];
    }
    for (int kk = n - 1; kk >= 3; --kk) {
        int l = max(1, kk - 2);
        cout << "? " << l << " " << current_min_pos << endl;
        cout.flush();
        char c;
        cin >> c;
        bool l_gt_min = (c == '>');
        int assign_p;
        if (!l_gt_min) {
            // l < min < max
            assign_p = current_max_pos;
            int temp = current_max_pos;
            current_max_pos = current_min_pos;
            current_min_pos = l;
        } else {
            // l > min, compare to max
            cout << "? " << l << " " << current_max_pos << endl;
            cout.flush();
            char c2;
            cin >> c2;
            bool l_gt_max = (c2 == '>');
            if (l_gt_max) {
                assign_p = l;
                // pending unchanged
            } else {
                // min < l < max
                assign_p = current_max_pos;
                current_max_pos = l;
                // min unchanged
            }
        }
        ans[assign_p] = kk;
    }
    // now assign 2 and 1
    ans[current_max_pos] = 2;
    ans[current_min_pos] = 1;
    // output
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    return 0;
}
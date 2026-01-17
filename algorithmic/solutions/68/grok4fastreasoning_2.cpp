#include <bits/stdc++.h>
using namespace std;

void select_two(vector<int> group, int n) {
    int s = group.size();
    int p = n / 2;
    if (s <= 3) {
        vector<int> surv;
        for (int i : group) {
            cout << 0 << " " << i << endl;
            int x;
            cin >> x;
            if (x == 1) {
                surv.push_back(i);
            }
        }
        // pick first two
        cout << 1 << " " << surv[0] << " " << surv[1] << endl;
        return;
    }
    int t = p;
    int u = s - t;
    vector<int> tested(group.begin(), group.begin() + t);
    vector<int> untouch(group.begin() + t, group.end());
    int nums = 0;
    for (int i : tested) {
        cout << 0 << " " << i << endl;
        int x;
        cin >> x;
        if (x == 1) nums++;
    }
    if (nums == t) {
        select_two(untouch, n);
    } else {
        // pick first two from untouch
        cout << 1 << " " << untouch[0] << " " << untouch[1] << endl;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int p = n / 2;
        int ss = p + 3;
        int rr = n - ss;
        vector<int> current(n);
        for (int i = 0; i < n; i++) current[i] = i;
        for (int roundd = 0; roundd < rr; roundd++) {
            vector<int> news;
            for (int i : current) {
                cout << 0 << " " << i << endl;
                int x;
                cin >> x;
                if (x == 1) {
                    news.push_back(i);
                }
            }
            current = news;
        }
        // now current has ss pens
        select_two(current, n);
    }
    return 0;
}
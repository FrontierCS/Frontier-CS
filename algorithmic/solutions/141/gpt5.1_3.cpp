#include <bits/stdc++.h>
using namespace std;

bool ask_equal(int i, int j) {
    cout << "R" << endl;
    cout.flush();

    char resp;
    cout << "? " << i << endl;
    cout.flush();
    cin >> resp;  // ignore

    cout << "? " << j << endl;
    cout.flush();
    cin >> resp;
    return resp == 'Y';
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    vector<int> reps; // representatives of distinct cake types
    int distinct = 0;

    for (int i = 1; i <= n; ++i) {
        bool isNew = true;
        for (int r : reps) {
            if (ask_equal(i, r)) {
                isNew = false;
                break;
            }
        }
        if (isNew) {
            reps.push_back(i);
            ++distinct;
        }
    }

    cout << "! " << distinct << endl;
    cout.flush();
    return 0;
}
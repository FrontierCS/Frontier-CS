#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

int ask(int x, const vector<int>& S) {
    cout << "? " << x << " " << S.size();
    for (int idx : S) cout << " " << idx;
    cout << endl;
    cout.flush();
    int resp;
    cin >> resp;
    if (resp == -1) {
        exit(0);
    }
    return resp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        if (n == -1) {
            exit(0);
        }
        int total = 2 * n - 1;
        bool found = false;
        for (int x = 1; x <= n; ++x) {
            // Binary search for an occurrence of x
            int l = 1, r = total;
            while (l < r) {
                int mid = (l + r) / 2;
                vector<int> S;
                for (int i = l; i <= mid; ++i) S.push_back(i);
                int resp = ask(x, S);
                if (resp == 1) {
                    r = mid;
                } else {
                    l = mid + 1;
                }
            }
            // l is an index where a[l] == x
            // Check if there is another occurrence
            vector<int> complement;
            for (int i = 1; i <= total; ++i) {
                if (i != l) complement.push_back(i);
            }
            int resp = ask(x, complement);
            if (resp == 0) {
                cout << "! " << x << endl;
                cout.flush();
                found = true;
                break;
            }
        }
        if (!found) {
            // Should not happen
        }
    }
    return 0;
}
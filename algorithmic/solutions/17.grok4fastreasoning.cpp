#include <bits/stdc++.h>
using namespace std;

int main() {
    int T;
    cin >> T;
    for(int t = 0; t < T; t++) {
        int n;
        cin >> n;
        cout << "? 1 " << n << endl;
        fflush(stdout);
        int p;
        cin >> p;
        int low, high;
        if(p == 1) {
            low = 2;
            high = n;
        } else if(p == n) {
            low = 1;
            high = n - 1;
        } else {
            cout << "? 1 " << p << endl;
            fflush(stdout);
            int res;
            cin >> res;
            if(res == p) {
                low = 1;
                high = p - 1;
            } else {
                low = p + 1;
                high = n;
            }
        }
        while(low < high) {
            int mid = (low + high) / 2;
            int lq, rq;
            if(high < p) {
                lq = mid + 1;
                rq = p;
            } else {
                lq = p;
                rq = mid;
            }
            cout << "? " << lq << " " << rq << endl;
            fflush(stdout);
            int res;
            cin >> res;
            if(high < p) {
                if(res == p) {
                    low = mid + 1;
                } else {
                    high = mid;
                }
            } else {
                if(res == p) {
                    high = mid;
                } else {
                    low = mid + 1;
                }
            }
        }
        cout << "! " << low << endl;
        fflush(stdout);
    }
    return 0;
}
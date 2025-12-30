#include <bits/stdc++.h>

using namespace std;

int main() {
    int t;
    cin >> t;
    for(int test = 0; test < t; test++) {
        int lo = 1, hi = 100000;
        while(lo < hi) {
            int mid = (lo + hi + 1) / 2;
            cout << "? 1 " << mid << endl << flush;
            int res;
            cin >> res;
            if(res == -1) return 0;
            if(res == 1) {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        cout << "! " << lo << endl << flush;
    }
    return 0;
}
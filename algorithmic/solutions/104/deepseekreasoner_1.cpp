#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int x;
    cin >> x;
    return x;
}

bool guess(int a) {
    cout << "! " << a << endl;
    cout.flush();
    int y;
    cin >> y;
    return y == 1;
}

void solve() {
    int n;
    cin >> n;
    int l = 1, r = n;
    
    while (r - l + 1 > 2) {
        int mid = (l + r) / 2;
        int x1 = ask(l, mid);
        int x2 = ask(mid, r);
        int x3 = ask(mid, mid);
        int b1 = (mid - l + 1) - x1;
        int b2 = (r - mid + 1) - x2;
        int b3 = 1 - x3;
        
        if (b1 == 1 && b2 == 0 && b3 == 0) {
            if (guess(mid)) return;
            else break;
        }
        if ( (b1 == 0 && b2 == 0 && b3 == 1) ||
             (b1 == 1 && b2 == 1 && b3 == 0) ||
             (b1 == 0 && b2 == 1 && b3 == 1) ) {
            r = mid;
            continue;
        }
        if ( (b1 == 0 && b2 == 1 && b3 == 0) ||
             (b1 == 1 && b2 == 0 && b3 == 1) ||
             (b1 == 1 && b2 == 1 && b3 == 1) ) {
            l = mid;
            continue;
        }
        // ambiguous (0,0,0)
        int x4 = ask(l, mid - 1);
        int b4 = (mid - l) - x4;
        if (b4 == 1) {
            l = mid + 1;
        } else {
            int x5 = ask(mid + 1, r);
            int b5 = (r - mid) - x5;
            if (b5 == 1) {
                r = mid - 1;
            } else {
                break;
            }
        }
    }
    
    if (guess(l)) return;
    if (r > l) guess(r);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
        cout << "#" << endl;
        cout.flush();
    }
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int64 n;

int64 ask(int64 x, int64 y){
    cout << x << " " << y << endl;
    cout.flush();
    int64 r;
    if(!(cin >> r)) exit(0);
    if(r == 0) exit(0);
    return r;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if(!(cin >> n)) return 0;

    // Exponential search to find an upper bound for max(a,b)
    int64 prev = 0;
    int64 R = 1;
    int64 resp = ask(R, R);
    if(resp == 0) return 0;
    while((resp == 1 || resp == 2) && R < n){
        prev = R;
        if (R > n/2) R = n;
        else R *= 2;
        resp = ask(R, R);
        if(resp == 0) return 0;
    }
    // Now prev < max(a,b) <= R (unless already 0 and exited)

    // Binary search to find M = max(a,b)
    int64 low = max<int64>(1, prev + 1), high = R;
    while(low < high){
        int64 mid = low + (high - low) / 2;
        resp = ask(mid, mid);
        if(resp == 0) return 0;
        if(resp == 1 || resp == 2){
            low = mid + 1;
        }else{
            high = mid;
        }
    }
    int64 M = low;

    // Find b using x fixed to M:
    // Find minimal y such that response != 2 (i.e., y >= b)
    int64 l = 1, r = n;
    while(l < r){
        int64 mid = l + (r - l) / 2;
        resp = ask(M, mid);
        if(resp == 0) return 0;
        if(resp == 2){
            l = mid + 1;
        }else{
            r = mid;
        }
    }
    int64 b = l;

    // Check if done (if M == a and b found, (M,b) should be 0)
    resp = ask(M, b);
    if(resp == 0) return 0;

    // Otherwise, M == b, now find a with y fixed to b:
    l = 1; r = n;
    while(l < r){
        int64 mid = l + (r - l) / 2;
        resp = ask(mid, b);
        if(resp == 0) return 0;
        if(resp == 1){
            l = mid + 1;
        }else{
            r = mid;
        }
    }
    // Final confirmation (should be 0)
    ask(l, b);
    return 0;
}
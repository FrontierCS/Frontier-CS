/*
SOURCE: Shang Zhou
IIMOC SUBMISSION #1443
HUMAN BEST FOR POLYPACK (TRANSFORMATION OUTPUT FORMAT)
*/

#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    vector<int> inp(n);
    for (int i = 0; i < n; i++){
        cin >> inp[i];
    }
    int r, s, p, q;

    // greedily take out the longest increasing/decreasing subsequence each time

    // auto take_out = [&](vector<int> &v){
    //     int INF = (int)1e9;
    //     vector<int> dp(v.size() + 1, INF), prev(v.size() + 1, -1);
    //     for (int i = 0; i < v.size(); i++){
    //         int pos = lower_bound(dp.begin(), dp.end(), v[i]) - dp.begin();
    //         dp[pos] = v[i];
    //         prev[pos] = i;
    //     }
    //     int pos = lower_bound(dp.begin(), dp.end(), INF) - dp.begin();
    //     pos--;
    //     int cur = pos;
    //     while (cur != -1){
    //         v[cur] = -1;
    //         cur = prev[cur];
    //     }
    //     return pos;
    // };

    // vector<int> a, b, c, d;
    // while (take_out(inp) > 0){
    //     a.push_back(inp[0]);
    //     inp.erase(inp.begin());
    // }
    // while (take_out(inp) > 0){
    // }


    r = s = p = n / 4;
    q = n - r - s - p;
    cout << r << " " << s << " " << p << " " << q << endl;
    for (int i = 0; i < r; i++){
        cout << inp[i] << " ";
    }
    cout << endl;
    for (int i = 0; i < s; i++){
        cout << inp[r + i] << " ";
    }
    cout << endl;
    for (int i = 0; i < p; i++){
        cout << inp[r + s + i] << " ";
    }
    cout << endl;
    for (int i = 0; i < q; i++){
        cout << inp[r + s + p + i] << " ";
    }
    cout << endl;
    cerr << "here" << endl;
    return 0;
}
    
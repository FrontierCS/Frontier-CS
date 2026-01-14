#include <iostream>
#include <string>
#include <cmath>
using namespace std;

int main() {
    int b, w, x, y;
    cin >> b >> w >> x >> y;
    
    if (abs(b - w) <= 1) {
        // single row construction
        int r = 1;
        int c = b + w;
        string s(c, '.');
        if (b >= w) {
            for (int i = 0; i < c; ++i) {
                if (i % 2 == 0) s[i] = '@';
                else s[i] = '.';
            }
        } else {
            for (int i = 0; i < c; ++i) {
                if (i % 2 == 1) s[i] = '@';
                else s[i] = '.';
            }
        }
        cout << r << " " << c << "\n";
        cout << s << "\n";
    } else {
        // two-row construction
        int need_b = b - 1;
        int need_w = w - 1;
        int comb = min(need_b, need_w);
        int rem_b = need_b - comb;
        int rem_w = need_w - comb;
        
        string top = "@";
        string bottom = ".";
        
        for (int i = 0; i < comb; ++i) {
            top += "@.@";
            bottom += "@..";
        }
        for (int i = 0; i < rem_b; ++i) {
            top += ".@";
            bottom += "..";
        }
        for (int i = 0; i < rem_w; ++i) {
            top += "@@";
            bottom += "@.";
        }
        
        int r = 2;
        int c = top.size();
        cout << r << " " << c << "\n";
        cout << top << "\n";
        cout << bottom << "\n";
    }
    
    return 0;
}
#include <bits/stdc++.h>

using namespace std;

int main() {
    int b, w, x, y;
    cin >> b >> w >> x >> y;
    if (abs(b - w) <= 1) {
        int nn = b + w;
        int r = 1;
        int c = nn;
        cout << r << " " << c << endl;
        string s = "";
        bool cur_black = (b >= w);
        for (int i = 0; i < nn; i++) {
            if (cur_black) s += '@';
            else s += '.';
            cur_black = !cur_black;
        }
        cout << s << endl;
    } else {
        bool black_layer = (b < w);
        int minc = min(b, w);
        int maxc = max(b, w);
        char layer_c = black_layer ? '@' : '.';
        char split_c = black_layer ? '.' : '@';
        int kk = maxc - minc + 1;
        int c_large = 2 * kk + 1;
        int add_c = 2 * (minc - 1);
        int cc = c_large + add_c;
        int rr = 2;
        vector<string> g(2, string(cc, ' '));
        // large block columns 0 to c_large-1
        for (int roww = 0; roww < 2; roww++) {
            for (int j = 0; j < c_large; j++) {
                if (roww == 0) { // top
                    if (j % 2 == 1) g[roww][j] = split_c;
                    else g[roww][j] = layer_c;
                } else { // bottom
                    g[roww][j] = layer_c;
                }
            }
        }
        // additional
        int jbase = c_large;
        for (int ii = 0; ii < add_c; ii++) {
            int j = jbase + ii;
            char ch;
            if (ii % 2 == 0) ch = split_c; // split
            else ch = layer_c; // layer
            g[0][j] = ch;
            g[1][j] = ch;
        }
        cout << rr << " " << cc << endl;
        for (int roww = 0; roww < rr; roww++) {
            cout << g[roww] << endl;
        }
    }
    return 0;
}
#include <iostream>
#include <string>
using namespace std;

int main() {
    int b, w, x, y;
    cin >> b >> w >> x >> y;
    
    if (b == 1 && w == 1) {
        cout << "1 2\n";
        cout << "@.\n";
        return 0;
    }
    
    if (b == 1) {
        int cols = 2 * w - 1;
        cout << "3 " << cols << "\n";
        string row1(cols, '@');
        string row2;
        for (int i = 0; i < cols; ++i) {
            row2 += (i % 2 == 0 ? '.' : '@');
        }
        string row3(cols, '@');
        cout << row1 << "\n" << row2 << "\n" << row3 << "\n";
        return 0;
    }
    
    if (w == 1) {
        int cols = 2 * b - 1;
        cout << "3 " << cols << "\n";
        string row1(cols, '.');
        string row2;
        for (int i = 0; i < cols; ++i) {
            row2 += (i % 2 == 0 ? '@' : '.');
        }
        string row3(cols, '.');
        cout << row1 << "\n" << row2 << "\n" << row3 << "\n";
        return 0;
    }
    
    // b >= 2, w >= 2
    int b1 = b - 1;
    int w1 = w - 1;
    
    string left_row1, left_row2, left_row3;
    int L_cols;
    if (b1 == 1) {
        L_cols = 2;
        left_row1 = "..";
        left_row2 = "@.";
        left_row3 = "..";
    } else {
        L_cols = 2 * b1 - 1;
        left_row1 = string(L_cols, '.');
        left_row2 = string(L_cols, ' ');
        for (int i = 0; i < L_cols; ++i) {
            left_row2[i] = (i % 2 == 0 ? '@' : '.');
        }
        left_row3 = string(L_cols, '.');
    }
    
    string right_row1, right_row2, right_row3;
    int R_cols;
    if (w1 == 1) {
        R_cols = 2;
        right_row1 = "@@";
        right_row2 = ".@";
        right_row3 = "@@";
    } else {
        R_cols = 2 * w1 - 1;
        right_row1 = string(R_cols, '@');
        right_row2 = string(R_cols, ' ');
        for (int i = 0; i < R_cols; ++i) {
            right_row2[i] = (i % 2 == 0 ? '.' : '@');
        }
        right_row3 = string(R_cols, '@');
    }
    
    int cols = L_cols + R_cols;
    cout << "3 " << cols << "\n";
    cout << left_row1 + right_row1 << "\n";
    cout << left_row2 + right_row2 << "\n";
    cout << left_row3 + right_row3 << "\n";
    
    return 0;
}
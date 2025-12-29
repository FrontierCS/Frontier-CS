#include <iostream>

using namespace std;

int main() {
    int initialDeep;
    cin >> initialDeep;
    if (initialDeep == 0) {
        return 0;
    }
    int cur_d = initialDeep;
    while (true) {
        bool found = false;
        for (int i = 0; i < 2; ++i) {
            cout << "move " << i << endl;
            int res;
            cin >> res;
            if (res == 1) {
                return 0;
            }
            cout << "query" << endl;
            int new_d;
            cin >> new_d;
            if (new_d < cur_d) {
                cur_d = new_d;
                found = true;
                break;
            } else {
                cout << "move " << i << endl;
                cin >> res;
                if (res == 1) {
                    return 0;
                }
            }
        }
        if (!found) {
            cout << "move 2" << endl;
            int res;
            cin >> res;
            if (res == 1) {
                return 0;
            }
            --cur_d;
        }
    }
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

bool ask(int mid) {
    cout << "? " << mid;
    for (int i = 1; i <= mid; ++i)
        cout << " " << i;
    cout << endl;
    cout.flush();
    string s;
    cin >> s;
    return s == "YES";
}

void guess(int g) {
    cout << "! " << g << endl;
    cout.flush();
    string s;
    cin >> s;
    if (s == ":)")
        exit(0);
}

int main() {
    int n;
    cin >> n;
    int l = 1, r = n;
    while (r - l + 1 > 2) {
        int mid = (l + r) / 2;
        bool a1 = ask(mid);
        bool a2 = ask(mid);
        if (a1 == a2) {
            if (a1)
                r = mid;
            else
                l = mid + 1;
        } else {
            bool a3 = ask(mid);
            int cntY = (a1 ? 1 : 0) + (a2 ? 1 : 0) + (a3 ? 1 : 0);
            if (cntY >= 2)
                r = mid;
            else
                l = mid + 1;
        }
    }
    guess(l);
    if (l != r)
        guess(r);
    return 0;
}
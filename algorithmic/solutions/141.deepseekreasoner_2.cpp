#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    int distinct = 0;
    for (int i = 1; i <= n; i++) {
        cout << "? " << i << endl;
        cout.flush();
        char resp;
        cin >> resp;
        if (resp == 'N') distinct++;
    }
    cout << "! " << distinct << endl;
    return 0;
}
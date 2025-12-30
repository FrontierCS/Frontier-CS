#include <iostream>
#include <string>
#include <cstdlib>
#include <ctime>

using namespace std;

int main() {
    srand(time(0));
    int m;
    cin >> m;
    string response;
    cin >> response; // first response is "center"
    
    int moves = 0;
    while (moves < 50000) {
        int passage = rand() % m;
        cout << "0 left " << passage << endl;
        moves++;
        
        cin >> response;
        if (response == "treasure") {
            break;
        }
    }
    return 0;
}
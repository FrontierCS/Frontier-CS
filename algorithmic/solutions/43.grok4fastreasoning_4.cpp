#include <bits/stdc++.h>

using namespace std;

int main() {
  int N = 50, M = 50;
  cout << N << " " << M << endl;
  for(int i = 1; i <= N; i++) {
    for(int j = 1; j <= M; j++) {
      char c = '.';
      if(i == 50 && j == 50) c = 'P';
      if(i >= 2 && i <= 3 && j >= 2 && j <= 3) c = 'B';
      if(i >= 48 && i <= 49 && j >= 48 && j <= 49) c = 'S';
      cout << c;
    }
    cout << endl;
  }
  return 0;
}
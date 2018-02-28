#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QLineEdit>

namespace Ui {
class KeyboardLineEdit;
}

class KeyboardLineEdit : public QLineEdit
{
    Q_OBJECT

public:
    explicit KeyboardLineEdit(QWidget *parent = 0);
    ~KeyboardLineEdit();

private:
    Ui::KeyboardLineEdit *ui;
};

#endif // MAINWINDOW_H

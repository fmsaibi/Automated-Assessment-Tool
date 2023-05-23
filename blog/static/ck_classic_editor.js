var editor = ClassicEditor
    .create(document.querySelector('#editor'), {
        toolbar: ['heading', '|', 'bold', 'italic', 'underline', 'numberedList', 'bulletedList', 'indent', 'outdent', '|', 'undo', 'redo'],
        heading: {
            options: [
                { model: 'paragraph', title: 'Paragraph', class: 'ck-heading_paragraph' },
                { model: 'heading1', view: 'h1', title: 'Heading 1', class: 'ck-heading_heading1' },
                { model: 'heading2', view: 'h2', title: 'Heading 2', class: 'ck-heading_heading2' },
                { model: 'heading3', view: 'h3', title: 'Heading 3', class: 'ck-heading_heading3' },
                { model: 'heading4', view: 'h4', title: 'Heading 4', class: 'ck-heading_heading4' },
                { model: 'heading5', view: 'h5', title: 'Heading 5', class: 'ck-heading_heading5' },
                { model: 'heading6', view: 'h6', title: 'Heading 6', class: 'ck-heading_heading6' },
                { model: 'smallText', view: { name:'small' }, title:'Small Text', class:'ck-heading_smallText'}
            ]
        }
    })
    .catch(error => {
        console.error(error);
    });



var editorReason = ClassicEditor
    .create(document.querySelector('#editor-reason'), {
        toolbar: ['heading', '|', 'bold', 'italic', 'underline', 'numberedList', 'bulletedList', 'indent', 'outdent', '|', 'undo', 'redo']
    })
    .catch(error => {
        console.error(error);
    });
